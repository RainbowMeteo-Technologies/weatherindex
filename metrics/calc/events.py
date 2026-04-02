import functools
import multiprocessing
import numpy as np
import os
import pandas
import shutil
import typing
import uuid

from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass

from metrics.calc.evaluators import get_evaluator
from metrics.calc.forecast_manager import DataVendor, ForecastManager
from metrics.calc.utils import read_selected_sensors
from metrics.session import Session
from metrics.utils.frame import concat_frames
from metrics.utils.time import floor_timestamp

from rich.console import Console
from tqdm import tqdm


console = Console()


@dataclass
class JobParams:
    """
    Attributes
    ----------
    forecast_vendor : DataVendor
        Vendor of comparable forecast data
    observation_vendor : DataVendor
        Vendor of comparable observable data
    sensors_ids : List[str]
        List of sensors that should be used to compare. If list is empty then all sensors will be used
    forecast_offsets : List[int]
        Forecast offsets (in minutes) for which metrics should be calculated
    evaluator : typing.Callable[[pandas.DataFrame, pandas.DataFrame], list[list[any]]]
        Evaluator to use to calculate metrics
    sesssion_path : str
        Path to the session directory
    sensors_path : str
        Path to a directory with sensors data
    time_range : Tuple[int, int]
        Sensors timestamp range to calculate metrics
    observations_offset: int
        Offset for observations comparing to forecast (in seconds)
    group_period: int
        Grouping period to aggregate events timestamps (in seconds)
    """
    forecast_vendor: DataVendor
    observation_vendor: DataVendor
    sensor_ids: typing.List[str]
    forecast_offsets: typing.List[int]
    session_path: str
    time_range: typing.Tuple[int, int]
    output_path: str
    evaluator: typing.Callable[[pandas.DataFrame, pandas.DataFrame], list[list[any]]]
    observations_offset: int = 0
    group_period: int = 600
    forecast_manager_cls: typing.Type[ForecastManager] = ForecastManager


# MARK: Multiprocess Job
class Worker:
    def __init__(self, params: JobParams) -> None:
        self._params = params

    def _get_sensor_file_list(self, sensors_time_range: typing.Tuple[int, int], sensors_path: str) -> typing.List[str]:
        """Returns list of sensor files that should be loaded

        Parameters
        ----------
        sensors_time_range : Tuple[int, int]
            Range of timestamps that should be loaded
        sensors_path : str
            Path to a directory with sensor files
        """

        files_list = os.listdir(sensors_path)

        def _should_process_file(file_name: str) -> bool:
            file_path = os.path.join(sensors_path, file_name)
            if os.path.isfile(file_path) and file_name.endswith(".parquet"):
                try:
                    timestamp = int(file_name.replace(".parquet", ""))
                    return sensors_time_range[0] <= timestamp <= sensors_time_range[1]
                except ValueError:
                    return False

            return False

        filtered_files = list(filter(_should_process_file, files_list))

        return [os.path.join(sensors_path, file_name) for file_name in filtered_files]

    def run(self) -> None:
        """Runs metrics calculation

        Returns
        -------
        pandas.DataFrame
            Calculated metrics for each sensor id, forecast offset, timestamp
        """
        session = Session.create_from_folder(self._params.session_path)
        sensors_path = None
        sensors_path = os.path.join(session.tables_folder, self._params.observation_vendor.value)

        sensors_start_time, sensors_end_time = self._params.time_range
        sensors_start_time = sensors_start_time - self._params.group_period

        sensors_time_range = (sensors_start_time, sensors_end_time)

        collected_sensor_files = self._get_sensor_file_list(sensors_time_range=sensors_time_range,
                                                            sensors_path=sensors_path)

        console.log(f"Load sensors {collected_sensor_files}")
        loaded_tables = []
        for file_path in collected_sensor_files:
            if os.path.exists(file_path):
                loaded_tables.append(pandas.read_parquet(file_path))

        sensor_observations = concat_frames(frames=loaded_tables,
                                            columns=["id",
                                                     "lon", "lat",
                                                     "timestamp",
                                                     "precip_rate", "precip_type",
                                                     "px", "py",
                                                     "tile_x", "tile_y",
                                                     "sky_condition"])

        # check if need filtering
        if len(self._params.sensor_ids) > 0:
            console.log(f"Filtering sensors {sensors_time_range} based on found ids")
            sensor_observations = sensor_observations[sensor_observations["id"].isin(self._params.sensor_ids)]
            console.log(f"{len(sensor_observations)} observations stayed after filtering for {sensors_time_range}")

        # leave only sensors in the measured range
        filter = (sensor_observations["timestamp"] > sensors_time_range[0]) & \
            (sensor_observations["timestamp"] <= sensors_time_range[1])
        sensor_observations = sensor_observations[filter]

        # TODO: support probability thresholds

        # drop duplicates
        console.log(f"Sorting sensors from range {sensors_time_range}")
        sensor_observations = sensor_observations.sort_values(by=["id", "timestamp"])
        sensor_observations = sensor_observations.drop_duplicates(subset=["id", "timestamp"], keep="first")

        forecast_start_time, forecast_end_time = self._params.time_range
        # -1:10, to cover begin of observations with 2 hour forecast
        forecast_start_time = forecast_start_time - (max(self._params.forecast_offsets) + 4200)

        console.log(f"Loading forecast in range ({forecast_start_time}, {forecast_end_time})...")

        data_provider = self._params.forecast_manager_cls(data_vendor=self._params.forecast_vendor, session=session)
        forecast = data_provider.load_forecast(time_rage=(forecast_start_time, forecast_end_time),
                                               sensors_table=sensor_observations)

        console.log(f"Calculating metrics for {self._params.time_range}...")

        calculated_frame = self._calculate(forecast_times=self._params.forecast_offsets,
                                           observations=sensor_observations,
                                           forecast=forecast)

        self._dump_frame(calculated_frame)

    def _dump_frame(self, frame: pandas.DataFrame):

        os.makedirs(self._params.output_path, exist_ok=True)
        frame.to_csv(os.path.join(self._params.output_path,
                                  f"{uuid.uuid4().hex}.csv"),
                     index=False)

    def _align_time_column(self, data: pandas.DataFrame,
                           column_name: str,
                           period: int,
                           offset: int = 0) -> pandas.DataFrame:
        """Does inplace timestamp aligment of the column. Values in range (0, 10m] will be aligned to 10m

        Parameters
        ----------
        data : pandas.DataFrame
            Table to align time
        column_name : str
            Name of the column to do aignment
        period : int
            Period in seconds to align timestamps
        offset : int
            Time offset in seconds to apply on aligned column

        Returns
        -------
        pandas.DataFrame
            Returns the same data table, but with aligned column
        """
        data[column_name] = (np.ceil((data[column_name] + offset) / period) * period).astype(np.int64)

        return data

    def _calculate(self,
                   forecast_times: typing.List[int],
                   observations: pandas.DataFrame,
                   forecast: pandas.DataFrame) -> pandas.DataFrame:
        """Implements calculation of metrics. This function takes two tables: observation, forecast.
        Data in both tables resampled by 10 minutes (using max value of precip_rate).

        Parameters
        ----------
        forecast_times : List[int]
            List of forecast times (in seconds) to calculate metrics
        observations : pandas.DataFrame
            Table of observations. Each observation has timestamp and id
        forecast : pandas.DataFrame
            Table of forecasted values. Each value has id and forecast time

        Returns
        -------
        pandas.DataFrame
            Calculated metrics for each forecast offset per sensor ID & timestamp
        """
        observations = observations.sort_values(by=["id", "timestamp"])
        observations = observations.drop_duplicates(subset=["id", "timestamp"], keep="first")

        # ceil forecast time to 10 minutes
        forecast = self._align_time_column(data=forecast,
                                           column_name="forecast_time",
                                           period=self._params.group_period,
                                           offset=self._params.observations_offset)
        forecast = self._align_time_column(data=forecast,
                                           column_name="timestamp",
                                           period=self._params.group_period,
                                           offset=self._params.observations_offset)

        forecast = forecast.groupby(["id", "timestamp", "forecast_time", "precip_type"]).agg({
            "precip_rate": "max"
        }).reset_index()

        forecast = forecast[forecast["forecast_time"].isin(forecast_times)]

        # resample observations
        observations = self._align_time_column(data=observations,
                                               column_name="timestamp",
                                               period=self._params.group_period,
                                               offset=self._params.observations_offset)

        observations = observations.groupby(["id", "timestamp", "precip_type"]).agg({
            "precip_rate": "max"
        }).reset_index()

        console.log(f"Observations:\n{observations}")
        console.log(f"Forecast:\n{forecast}")

        collected_events = []

        grouped_observations = observations.groupby(["id", "timestamp"])
        grouped_forecasts = forecast.groupby(["id", "timestamp", "forecast_time"])

        for (sensor_id, timestamp, forecast_time), sensor_forecast_time_data in grouped_forecasts:
            sensor_time_key = (sensor_id, timestamp)

            if sensor_time_key not in grouped_observations.groups:
                continue

            sensor_observations_data = grouped_observations.get_group(sensor_time_key)

            assert sensor_observations_data["id"].unique() == [sensor_id], \
                f"Expected only one sensor id {sensor_id}, got {sensor_observations_data['id'].unique()}"
            assert sensor_observations_data["timestamp"].unique() == [timestamp], \
                f"Expected only one timestamp {timestamp}, got {sensor_observations_data['timestamp'].unique()}"

            assert sensor_forecast_time_data["id"].unique() == [sensor_id], \
                f"Expected only one sensor id {sensor_id}, got {sensor_forecast_time_data['id'].unique()}"
            assert sensor_forecast_time_data["timestamp"].unique() == [timestamp], \
                f"Expected only one timestamp {timestamp}, got {sensor_forecast_time_data['timestamp'].unique()}"
            assert sensor_forecast_time_data["forecast_time"].unique() == [forecast_time], \
                f"Expected only one forecast time {forecast_time}, got {sensor_forecast_time_data['forecast_time'].unique()}"

            sensor_event_data = self._params.evaluator(sensor_observations_data, sensor_forecast_time_data)
            collected_events.extend(sensor_event_data)

        console.log(f"Collected {len(collected_events)} events")

        assert all(len(event) == 9 for event in collected_events), \
            f"Expected 9 columns in each event, but got {collected_events[0]}"

        result_metrics = pandas.DataFrame(
            collected_events,
            columns=[
                "id",
                "timestamp",
                "precip_type_observations",
                "precip_rate_observations",
                "observed_precip",
                "forecast_time",
                "precip_type_forecast",
                "precip_rate_forecast",
                "forecasted_precip"])

        result_metrics["tp"] = 0
        result_metrics["fp"] = 0
        result_metrics["tn"] = 0
        result_metrics["fn"] = 0

        result_metrics.loc[(result_metrics["forecasted_precip"]) & (result_metrics["observed_precip"]), "tp"] = 1
        result_metrics.loc[(result_metrics["forecasted_precip"]) & (~result_metrics["observed_precip"]), "fp"] = 1
        result_metrics.loc[(~result_metrics["forecasted_precip"]) & (~result_metrics["observed_precip"]), "tn"] = 1
        result_metrics.loc[(~result_metrics["forecasted_precip"]) & (result_metrics["observed_precip"]), "fn"] = 1

        console.log(f"Metrics (forecast - {self._params.forecast_vendor.value}, "
                    f"observations - {self._params.observation_vendor.value}, "
                    f"session_path - {self._params.session_path}):\n"
                    f"{result_metrics}")

        return result_metrics


def _process_time_range(params: JobParams):
    try:
        worker = Worker(params=params)
        return worker.run()
    except Exception:
        console.print_exception()

# MARK: Job Management


class CalculateMetrics:
    def __init__(self,
                 forecast_vendor: DataVendor,
                 observation_vendor: DataVendor,
                 sensor_selection_path: typing.Optional[str],
                 forecast_offsets: typing.List[int],
                 evaluator: typing.Callable[[pandas.DataFrame, pandas.DataFrame], list[list[any]]],
                 session_path: str,
                 observations_offset: int = 0,
                 split_time_range: int = 3600,
                 group_period: int = 600,
                 forecast_manager_cls: typing.Type[ForecastManager] = ForecastManager) -> None:
        """
        Parameters
        ----------
        data_vendor : DataVendor
            Data vendor that should be used to compare with sensors
        sensor_selection_path : typing.Optional[str]
            Optional path to directory or file where to find tables with sensor id's for comparing.
            If this directory is provided, then only sensors that were found in this directory will be used
        forecast_offsets : List[int]
            List of forecast offset (in seconds) to calculate metrics for.
        evaluator : typing.Callable[[pandas.DataFrame, pandas.DataFrame], list[list[any]]]
            Evaluator to use to calculate metrics
        session_path : str
            Path to a session directory
        sensors_path : str
            Path to a directory with sensor tables
        """
        self._forecast_vendor = forecast_vendor
        self._observation_vendor = observation_vendor
        self._sensor_selection_path = sensor_selection_path
        self._forecast_offsets = forecast_offsets
        self._evaluator = evaluator
        self._session_path = session_path
        self._observations_offset = observations_offset
        self._split_time_range = split_time_range
        self._group_period = group_period
        self._forecast_manager_cls = forecast_manager_cls

        self._session = Session.create_from_folder(session_path)

    @property
    def metrics_path(self) -> str:
        return os.path.join(self._session.metrics_folder,
                            f"{self._forecast_vendor.value}.{self._observation_vendor.value}.csv")

    @property
    def partial_metrics_dir(self) -> str:
        return os.path.join(self._session.metrics_folder,
                            f"temp_{self._forecast_vendor.value}_{self._observation_vendor.value}")

    def _calc_sensors_range(self) -> typing.Tuple[int, int]:
        """Calculates aligned sensors range based on session start/end time

        Returns
        -------
        Tuple[int, int]
            Session time range aligned to `self._split_time_range`
        """
        session = Session.create_from_folder(self._session_path)

        start_time = floor_timestamp(session.start_time, self._split_time_range)
        end_time = floor_timestamp(session.end_time, self._split_time_range)
        if end_time < session.end_time:
            end_time += self._split_time_range

        return (start_time, end_time)

    def collect_jobs(self) -> typing.List[typing.Callable[[], None]]:
        selected_sensors = read_selected_sensors(self._sensor_selection_path)
        selected_sensors = selected_sensors.drop_duplicates(subset=["id"], keep="first")
        selected_sensors_ids = selected_sensors["id"].unique()

        # Calculate metrics in this way:
        # - split session time by 1 hour ranges
        # - calculate metrics for each 1 hour range

        start_time, end_time = self._calc_sensors_range()

        jobs = []
        for timestamp in range(start_time, end_time, self._split_time_range):
            jobs.append(JobParams(forecast_vendor=self._forecast_vendor,
                                  observation_vendor=self._observation_vendor,
                                  forecast_offsets=self._forecast_offsets,
                                  session_path=self._session_path,
                                  time_range=(timestamp, timestamp + self._split_time_range),
                                  sensor_ids=selected_sensors_ids,
                                  evaluator=self._evaluator,
                                  observations_offset=self._observations_offset,
                                  group_period=self._group_period,
                                  forecast_manager_cls=self._forecast_manager_cls,
                                  output_path=self.partial_metrics_dir))

        return [functools.partial(_process_time_range, params=job) for job in jobs]

    def calculate(self, process_num: int = 1) -> None:
        with ProcessPoolExecutor(max_workers=process_num,
                                 mp_context=multiprocessing.get_context("spawn")) as executor:
            futures = [executor.submit(job) for job in self.collect_jobs()]
            for _ in tqdm(as_completed(futures),
                          total=len(futures),
                          desc="Calculating metrics...",
                          ascii=True):
                pass

        frames = []
        for filename in os.listdir(self.partial_metrics_dir):
            if filename.endswith(".csv"):
                frames.append(pandas.read_csv(os.path.join(self.partial_metrics_dir, filename)))

        if len(frames) == 0:
            console.log(f"Found no frames at {self.partial_metrics_dir}")

        final_metrics = concat_frames(frames, columns=["id",
                                                       "timestamp", "forecast_time",
                                                       "precip_type_status_forecast",
                                                       "precip_rate_forecast",
                                                       "precip_type_status_observations",
                                                       "precip_rate_observations",
                                                       "forecasted_precip", "observed_precip",
                                                       "tp", "fp", "tn", "fn"])
        final_metrics.to_csv(self.metrics_path, index=False)

        shutil.rmtree(self.partial_metrics_dir, ignore_errors=True)


def calc_events(session_path: str,
                forecast_vendor: DataVendor,
                observation_vendor: DataVendor,
                forecast_offsets: typing.List[int],
                observations_offset: int,
                evaluator: str,
                sensor_selection_path: str,
                process_num: int,
                output_csv: str,
                forecast_manager_cls: typing.Type[ForecastManager] = ForecastManager) -> pandas.DataFrame:
    calculator = CalculateMetrics(session_path=session_path,
                                  forecast_vendor=forecast_vendor,
                                  observation_vendor=observation_vendor,
                                  forecast_offsets=forecast_offsets,
                                  evaluator=get_evaluator(evaluator),
                                  observations_offset=observations_offset,
                                  sensor_selection_path=sensor_selection_path,
                                  forecast_manager_cls=forecast_manager_cls)

    calculator.calculate(process_num=process_num)

    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    shutil.move(calculator.metrics_path, output_csv)
