import multiprocessing
import numpy as np
import os
import pandas
import typing

from dataclasses import dataclass
from metrics.calc.forecast_manager import ForecastManager, DataVendor
from metrics.calc.utils import read_selected_sensors
from metrics.session import Session
from metrics.utils.precipitation import PrecipitationType
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
    threshold : float
        Threshold of the precipitation in mm/h
    precip_types : List[int]
        List of types which is considered to be an precip event
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
    threshold: float
    precip_types: typing.List[int]
    session_path: str
    time_range: typing.Tuple[int, int]
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

    def run(self) -> pandas.DataFrame:
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

        sensor_observations = pandas.concat(loaded_tables)

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
        return self._calculate(forecast_times=self._params.forecast_offsets,
                               observations=sensor_observations,
                               forecast=forecast)

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

        forecast["precip_type_status"] = forecast["precip_type"].isin(self._params.precip_types)
        forecast = forecast.groupby(["id", "timestamp", "precip_type_status", "forecast_time"]).agg({
            "precip_rate": "max"
        }).reset_index()

        forecast = forecast[forecast["forecast_time"].isin(forecast_times)]

        # resample observations
        observations = self._align_time_column(data=observations,
                                               column_name="timestamp",
                                               period=self._params.group_period,
                                               offset=self._params.observations_offset)

        observations["precip_type_status"] = observations["precip_type"].isin(self._params.precip_types)
        observations = observations.groupby(["id", "timestamp", "precip_type_status"]).agg({
            "precip_rate": "max"
        }).reset_index()

        print(f"Observations:\n{observations}")
        print(f"Forecast:\n{forecast}")

        result_metrics = pandas.merge(forecast, observations,
                                      on=["id", "timestamp"],
                                      how="inner",
                                      suffixes=("_forecast", "_observations"))

        result_metrics["forecasted_precip"] = ((result_metrics["precip_rate_forecast"] > self._params.threshold) &
                                               result_metrics["precip_type_status_forecast"])

        result_metrics["observed_precip"] = ((result_metrics["precip_rate_observations"] > self._params.threshold) &
                                             result_metrics["precip_type_status_observations"])

        result_metrics["tp"] = 0
        result_metrics["fp"] = 0
        result_metrics["tn"] = 0
        result_metrics["fn"] = 0

        result_metrics.loc[(result_metrics["forecasted_precip"]) & (result_metrics["observed_precip"]), "tp"] = 1
        result_metrics.loc[(result_metrics["forecasted_precip"]) & (~result_metrics["observed_precip"]), "fp"] = 1
        result_metrics.loc[(~result_metrics["forecasted_precip"]) & (~result_metrics["observed_precip"]), "tn"] = 1
        result_metrics.loc[(~result_metrics["forecasted_precip"]) & (result_metrics["observed_precip"]), "fn"] = 1

        print(f"Metrics (forecast - {self._params.forecast_vendor.value}, "
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
                 threshold: float,
                 precip_types: typing.List[PrecipitationType],
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
        threshold : float
            Threshold of precipitation rate in mm/h
        precip_types : List[PrecipitationType]
            List of types which is considered to be an precip event
        session_path : str
            Path to a session directory
        sensors_path : str
            Path to a directory with sensor tables
        """
        self._forecast_vendor = forecast_vendor
        self._observation_vendor = observation_vendor
        self._sensor_selection_path = sensor_selection_path
        self._forecast_offsets = forecast_offsets
        self._threshold = threshold
        self._precip_types = precip_types
        self._session_path = session_path
        self._observations_offset = observations_offset
        self._split_time_range = split_time_range
        self._group_period = group_period
        self._forecast_manager_cls = forecast_manager_cls

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

    def calculate(self, output_csv: str, process_num: int = 1) -> pandas.DataFrame:
        """
        Parameters
        ----------
        output_csv : str
            Path to the output CSV file
        process_num : int
            Number of parallel processes to run
        """
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
                                  threshold=self._threshold,
                                  precip_types=[precip_type.value for precip_type in self._precip_types],
                                  observations_offset=self._observations_offset,
                                  group_period=self._group_period,
                                  forecast_manager_cls=self._forecast_manager_cls))

        final_metrics: pandas.DataFrame = pandas.DataFrame()
        pool_ctx = multiprocessing.get_context("spawn")
        with pool_ctx.Pool(processes=process_num) as pool:
            for m in tqdm(pool.imap_unordered(_process_time_range, jobs),
                          desc="Calculating metrics...",
                          ascii=True,
                          total=len(jobs)):
                final_metrics = pandas.concat([final_metrics, m])
                final_metrics.to_csv(output_csv, index=False)

        return final_metrics


def calc_events(session_path: str,
                forecast_vendor: DataVendor,
                observation_vendor: DataVendor,
                forecast_offsets: typing.List[int],
                observations_offset: int,
                rain_threshold: float,
                sensor_selection_path: str,
                process_num: int,
                output_csv: str,
                forecast_manager_cls: typing.Type[ForecastManager] = ForecastManager) -> pandas.DataFrame:
    calculator = CalculateMetrics(session_path=session_path,
                                  forecast_vendor=forecast_vendor,
                                  observation_vendor=observation_vendor,
                                  forecast_offsets=forecast_offsets,
                                  rain_threshold=rain_threshold,
                                  observations_offset=observations_offset,
                                  sensor_selection_path=sensor_selection_path,
                                  forecast_manager_cls=forecast_manager_cls)

    calculator.calculate(output_csv=output_csv,
                         process_num=process_num)
