from itertools import product
import numpy as np
import os
import pandas
import pytest
import typing

from metrics.calc.events import CalculateMetrics, JobParams, Worker
from metrics.calc.forecast_manager import ForecastManager
from metrics.data_vendor import BaseDataVendor, DataVendor
from metrics.session import Session
from metrics.utils.metric import precision, recall, fscore
from metrics.utils.precipitation import PrecipitationType

from unittest.mock import MagicMock, patch


def _create_calculate_metrics(forecast_vendor: DataVendor = DataVendor.AccuWeather,
                              observation_vendor: DataVendor = DataVendor.Metar,
                              sensor_selection_path: typing.Optional[str] = None,
                              forecast_offsets: typing.List[int] = [0, 60, 120],
                              threshold: float = 0.1,
                              precip_types: typing.List[PrecipitationType] = [PrecipitationType.RAIN],
                              session_path: str = "test") -> CalculateMetrics:
    return CalculateMetrics(forecast_vendor=forecast_vendor,
                            observation_vendor=observation_vendor,
                            sensor_selection_path=sensor_selection_path,
                            forecast_offsets=forecast_offsets,
                            threshold=threshold,
                            precip_types=precip_types,
                            session_path=session_path)


def _create_worker(forecast_vendor: DataVendor = DataVendor.AccuWeather,
                   observation_vendor: DataVendor = DataVendor.Metar,
                   sensor_ids: typing.List[str] = [],
                   forecast_offsets: typing.List[int] = [0],
                   threshold: float = 0,
                   precip_types: typing.List[PrecipitationType] = [PrecipitationType.RAIN],
                   session_path: str = "test",
                   sensors_time_range: typing.Tuple[int, int] = (10800, 14400),
                   forecast_manager_cls: typing.Type[ForecastManager] = ForecastManager) -> Worker:
    return Worker(params=JobParams(forecast_vendor=forecast_vendor,
                                   observation_vendor=observation_vendor,
                                   sensor_ids=sensor_ids,
                                   forecast_offsets=forecast_offsets,
                                   threshold=threshold,
                                   precip_types=[precip_type.value for precip_type in precip_types],
                                   session_path=session_path,
                                   time_range=sensors_time_range,
                                   forecast_manager_cls=forecast_manager_cls))


def _create_observations(data: typing.List[any]) -> pandas.DataFrame:
    return pandas.DataFrame(columns=["id", "precip_rate", "precip_type", "timestamp"],
                            data=data)


def _create_forecast(data: typing.List[any]) -> pandas.DataFrame:
    return pandas.DataFrame(columns=["id", "precip_rate", "precip_type", "timestamp", "forecast_time"],
                            data=data)


def _create_metrics(tp: int = 0, tn: int = 0, fp: int = 0, fn: int = 0) -> any:
    return (tp, tn, fp, fn)


def _timestamp(timestamp: int, forecast_time: int = 0) -> int:
    return 15000 + timestamp + forecast_time


def _create_metrics_result(data: typing.List[any], columns: typing.List[str]) -> pandas.DataFrame:
    return pandas.DataFrame(data=data, columns=columns)


class TestWorker:
    @patch("metrics.calc.events.Session.create_from_folder")
    @patch("metrics.calc.events.pandas.read_parquet")
    def test_worker_smoke_run(self, read_parquet_mock, session_create_mock):
        forecast_manager_mock = MagicMock()
        forecast_manager_cls_mock = MagicMock()
        forecast_manager_cls_mock.return_value = forecast_manager_mock

        worker = _create_worker(forecast_manager_cls=forecast_manager_cls_mock)
        worker._get_sensor_file_list = MagicMock()
        worker._get_sensor_file_list.side_effect = ["1.parquet", "2.parquet"]

        observation_columns = ["id", "precip_type", "precip_rate", "timestamp"]
        read_parquet_mock.side_effect = [pandas.DataFrame(columns=observation_columns),
                                         pandas.DataFrame(columns=observation_columns)]

        forecast_columns = ["id", "forecast_time", "precip_type", "precip_rate", "timestamp"]
        forecast_manager_mock.load_forecast.side_effect = [pandas.DataFrame(columns=forecast_columns),
                                                           pandas.DataFrame(columns=forecast_columns)]

        worker.run()

    @pytest.mark.parametrize("files_list, time_range, expected_files_list", [
        (
            # files_list
            [
                ".",
                "..",
                "3500.parquet",
                "3500.test",
                "3600.parquet",
                "3700.parquet",
                "7200.parquet",
                "7201.parquet",
            ],
            # time_range
            (3600, 7200),
            # expected_files_list
            [
                "3600.parquet",
                "3700.parquet",
                "7200.parquet",
            ]
        ),
        # empty
        (
            # files_list
            [
                ".",
                "..",
                "non_number.parquet",
                "3500.parquet",
                "3500.test",
                "3600.parquet",
                "3700.parquet",
                "7200.parquet",
                "7201.parquet",
            ],
            # time_range
            (10800, 14400),
            # expected_files_list
            []
        )
    ])
    @patch("os.path.isfile")
    @patch("os.listdir")
    def test_get_sensor_file_list(self,
                                  mocked_files_list: any,
                                  mocked_is_file: any,
                                  files_list: typing.List[str],
                                  time_range: typing.Tuple[int, int],
                                  expected_files_list: typing.List[str]):

        mocked_files_list.return_value = files_list
        mocked_is_file.return_value = True

        worker = _create_worker()
        got_list = worker._get_sensor_file_list(sensors_time_range=time_range, sensors_path="test")
        got_list = sorted(got_list)
        expected_files_list = [os.path.join("test", file_name) for file_name in sorted(expected_files_list)]

        assert got_list == expected_files_list

    # NOTE: commented for current PR and will be implemented during metrics service implementation
    def test_run(self):
        # TODO: check that internal functions called with correct params
        assert True

    @pytest.mark.parametrize("data, column_name, period, expected_data", [
        (
            pandas.DataFrame(columns=["test_column"], data=[1600, 1200, 3601, 3599, 3600]),
            "test_column",
            600,
            pandas.DataFrame(columns=["test_column"], data=[1800, 1200, 4200, 3600, 3600])
        )
    ])
    def test_align_time_column(self,
                               data: pandas.DataFrame,
                               column_name: str,
                               period: int,
                               expected_data: pandas.DataFrame) -> pandas.DataFrame:

        worker = _create_worker()
        result = worker._align_time_column(data=data, column_name=column_name, period=period)

        print(result)
        print(expected_data)

        pandas.testing.assert_frame_equal(result.reset_index(drop=True),
                                          expected_data.reset_index(drop=True))

    @pytest.mark.parametrize("forecast_times, observations, forecast, expected_metrics", [
        # table columns:
        # - observations: "id", "precip_rate", "timestamp"
        # - forecast: "id", "precip_rate", "precip_type", "timestamp", "forecast_time"

        # smoke
        # This test does simple smoke test, that tp, tn, fp, fn metrics appears at specified time
        (
            # forecast_times
            [0, 600, 1800, 3600],
            # observations
            _create_observations([
                ("sensor_tp", 10.0, PrecipitationType.RAIN.value, _timestamp(7800, 60)),
                ("sensor_tn", 0.0, PrecipitationType.UNKNOWN.value, _timestamp(7800, 100)),
                ("sensor_fp", 0.0, PrecipitationType.UNKNOWN.value, _timestamp(7800, 1750)),
                ("sensor_fn", 10.0, PrecipitationType.RAIN.value, _timestamp(7800, 3540)),
            ]),
            # forecast
            _create_forecast([
                ("sensor_tp", 10.0, PrecipitationType.RAIN.value, _timestamp(7800, 60), 60),
                ("sensor_tn", 0.0, PrecipitationType.RAIN.value, _timestamp(7800, 100), 100),
                ("sensor_fp", 10.0, PrecipitationType.RAIN.value, _timestamp(7800, 1700), 1700),
                ("sensor_fn", 0.0, PrecipitationType.RAIN.value, _timestamp(7800, 3550), 3550)
            ]),
            # expected_metrics
            _create_metrics_result(data=(
                (600, *_create_metrics(tp=1, tn=1)),
                (1800, *_create_metrics(fp=1)),
                (3600, *_create_metrics(fn=1))
            ), columns=("forecast_time", "tp", "tn", "fp", "fn"))
        ),
        # time ceil
        # this test checks that events are grouped correctly by range (0; 10m] (excluding zero)
        (
            # forecast_times
            [0, 600, 1200],
            # observations
            _create_observations([
                # 0 minutes
                ("sensor_00:00", 10.0, PrecipitationType.RAIN.value, _timestamp(0, -1)),
                # 10 minutes
                ("sensor_00:01", 10.0, PrecipitationType.RAIN.value, _timestamp(0, 1)),
                ("sensor_09:59", 10.0, PrecipitationType.RAIN.value, _timestamp(0, 599)),
                ("sensor_10:00", 10.0, PrecipitationType.RAIN.value, _timestamp(0, 600)),
                # 20 minutes
                ("sensor_10:01", 10.0, PrecipitationType.RAIN.value, _timestamp(0, 601)),
                ("sensor_20:00", 10.0, PrecipitationType.RAIN.value, _timestamp(0, 1200)),
            ]),
            # forecast
            _create_forecast([
                # 0 minutes
                ("sensor_00:00", 10.0, PrecipitationType.RAIN.value, _timestamp(0, -1), 0),
                # 10 minutes
                ("sensor_00:01", 10.0, PrecipitationType.RAIN.value, _timestamp(0, 1), 600),
                ("sensor_09:59", 10.0, PrecipitationType.RAIN.value, _timestamp(0, 599), 600),
                ("sensor_10:00", 10.0, PrecipitationType.RAIN.value, _timestamp(0, 600), 600),
                # 20 minutes
                ("sensor_10:01", 10.0, PrecipitationType.RAIN.value, _timestamp(0, 601), 1200),
                ("sensor_20:00", 10.0, PrecipitationType.RAIN.value, _timestamp(0, 1200), 1200),
            ]),
            # expected_metrics
            _create_metrics_result(data=(
                (0, *_create_metrics(tp=1)),
                (600, *_create_metrics(tp=3)),
                (1200, *_create_metrics(tp=2))
            ), columns=("forecast_time", "tp", "tn", "fp", "fn"))
        ),
        # do not group different precip_type
        # this test checks that only rain precipitation used for metrics calculation
        (
            # forecast_times
            [0, 600],
            # observations
            _create_observations([
                # 0 minutes
                ("sensor_00:00", 10.0, PrecipitationType.RAIN.value, _timestamp(0)),
                # 10 minutes
                ("sensor_00:01", 10.0, PrecipitationType.SNOW.value, _timestamp(1)),
            ]),
            # forecast
            _create_forecast([
                # 0 minutes
                ("sensor_00:00", 10.0, PrecipitationType.RAIN.value, _timestamp(0), 0),
                # 10 minutes
                ("sensor_00:01", 10.0, PrecipitationType.RAIN.value, _timestamp(1), 1),
            ]),
            # expected_metrics
            _create_metrics_result(data=(
                (0, *_create_metrics(tp=1)),
                (600, *_create_metrics(fp=1))
            ), columns=("forecast_time", "tp", "tn", "fp", "fn"))
        ),
        # Observation duplicates
        (
            # forecast_times
            [0],
            # observations
            _create_observations([
                # 0 minutes
                ("sensor_00:00", 10.0, PrecipitationType.RAIN.value, _timestamp(0)),
                ("sensor_00:00", 10.0, PrecipitationType.RAIN.value, _timestamp(0)),
            ]),
            # forecast
            _create_forecast([
                # 0 minutes
                ("sensor_00:00", 10.0, PrecipitationType.RAIN.value, _timestamp(0), 0),
            ]),
            # expected_metrics
            _create_metrics_result(data=(
                (0, *_create_metrics(tp=1)),
            ), columns=("forecast_time", "tp", "tn", "fp", "fn"))
        ),
        # Maximum observation in 10 minutes. Checks that maximum value from the sensor was used
        (
            # forecast_times
            [0],
            # observations
            _create_observations([
                # 0 minutes
                ("sensor_10:00", 0.0, PrecipitationType.RAIN.value, _timestamp(1)),
                ("sensor_10:00", 0.0, PrecipitationType.RAIN.value, _timestamp(2 * 60)),
                ("sensor_10:00", 10.0, PrecipitationType.RAIN.value, _timestamp(5 * 60)),
            ]),
            # forecast
            _create_forecast([
                # 0 minutes
                ("sensor_10:00", 10.0, PrecipitationType.RAIN.value, _timestamp(10 * 60), 0),
            ]),
            # expected_metrics
            _create_metrics_result(data=(
                (0, *_create_metrics(tp=1)),
            ), columns=("forecast_time", "tp", "tn", "fp", "fn"))
        ),
    ])
    def test_calculate(self,
                       forecast_times: typing.List[int],
                       observations: pandas.DataFrame,
                       forecast: pandas.DataFrame,
                       expected_metrics: pandas.DataFrame):

        worker = _create_worker(forecast_offsets=forecast_times)

        result = worker._calculate(forecast_times=forecast_times,
                                   observations=observations,
                                   forecast=forecast)

        result = result.groupby(["forecast_time"])[["tp", "tn", "fp", "fn"]].sum().reset_index()

        merged_result = pandas.merge(expected_metrics,
                                     result,
                                     on="forecast_time",
                                     suffixes=("_expected", "_result"))

        for metric in ["tp", "tn", "fp", "fn"]:
            assert (merged_result[f"{metric}_expected"] ==
                    merged_result[f"{metric}_result"]).all(), f"Mismatch found in {metric}"

    @pytest.mark.parametrize("forecast_offsets, precip_types, observations, forecast, expected_metrics", [
        (
            [0, 600, 1200],
            [PrecipitationType.RAIN],
            _create_observations([
                ("sensor_1", 10.0, PrecipitationType.RAIN.value, _timestamp(0)),
                ("sensor_2", 0.0, PrecipitationType.RAIN.value, _timestamp(0))
            ]),
            _create_forecast([
                ("sensor_1", 10.0, PrecipitationType.RAIN.value, _timestamp(0), 0),
                ("sensor_1", 10.0, PrecipitationType.RAIN.value, _timestamp(0), 600),
                ("sensor_1", 10.0, PrecipitationType.RAIN.value, _timestamp(0), 1200),
                ("sensor_2", 10.0, PrecipitationType.RAIN.value, _timestamp(0), 0),
                ("sensor_2", 10.0, PrecipitationType.RAIN.value, _timestamp(0), 600),
                ("sensor_2", 10.0, PrecipitationType.RAIN.value, _timestamp(0), 1200),
            ]),
            _create_metrics_result(data=(
                (0, "sensor_1", *_create_metrics(tp=1)),
                (600, "sensor_1", *_create_metrics(tp=1)),
                (1200, "sensor_1", *_create_metrics(tp=1)),
                (0, "sensor_2", *_create_metrics(fp=1)),
                (600, "sensor_2", *_create_metrics(fp=1)),
                (1200, "sensor_2", *_create_metrics(fp=1))
            ), columns=("forecast_time", "sensor_id", "tp", "tn", "fp", "fn"))
        ),
        (
            [0],
            [PrecipitationType.RAIN],
            _create_observations([
                ("X", 10.0, PrecipitationType.RAIN.value, _timestamp(0)),
                ("Y", 0.0, PrecipitationType.UNKNOWN.value, _timestamp(0)),
                ("Z", 10.0, PrecipitationType.SNOW.value, _timestamp(0))
            ]),
            _create_forecast([
                ("X", 10.0, PrecipitationType.RAIN.value, _timestamp(0), 0),
                ("Y", 0.0, PrecipitationType.UNKNOWN.value, _timestamp(0), 0),
                ("Z", 10.0, PrecipitationType.SNOW.value, _timestamp(0), 0)
            ]),
            _create_metrics_result(data=[
                (0, "X", *_create_metrics(tp=1)),
                (0, "Y", *_create_metrics(tn=1)),
                (0, "Z", *_create_metrics(tn=1))
            ], columns=("forecast_time", "sensor_id", "tp", "tn", "fp", "fn"))
        ),
        (
            [0],
            [PrecipitationType.RAIN, PrecipitationType.SNOW],
            _create_observations([
                ("X", 10.0, PrecipitationType.SNOW.value, _timestamp(0)),
                ("Y", 0.0, PrecipitationType.UNKNOWN.value, _timestamp(0)),
                ("Z", 10.0, PrecipitationType.RAIN.value, _timestamp(0))
            ]),
            _create_forecast([
                ("X", 10.0, PrecipitationType.RAIN.value, _timestamp(0), 0),
                ("Y", 0.0, PrecipitationType.MIX.value, _timestamp(0), 0),
                ("Z", 10.0, PrecipitationType.SNOW.value, _timestamp(0), 0)
            ]),
            _create_metrics_result(data=[
                (0, "X", *_create_metrics(tp=1)),
                (0, "Y", *_create_metrics(tn=1)),
                (0, "Z", *_create_metrics(tp=1))
            ], columns=("forecast_time", "sensor_id", "tp", "tn", "fp", "fn"))
        ),
        (
            [0],
            [PrecipitationType.SNOW],
            _create_observations([
                ("X", 10.0, PrecipitationType.SNOW.value, _timestamp(0)),
                ("Y", 10.0, PrecipitationType.SNOW.value, _timestamp(0)),
                ("Z", 10.0, PrecipitationType.RAIN.value, _timestamp(0))
            ]),
            _create_forecast([
                ("X", 10.0, PrecipitationType.SNOW.value, _timestamp(0), 0),
                ("Y", 10.0, PrecipitationType.RAIN.value, _timestamp(0), 0),
                ("Z", 10.0, PrecipitationType.SNOW.value, _timestamp(0), 0)
            ]),
            _create_metrics_result(data=[
                (0, "X", *_create_metrics(tp=1)),
                (0, "Y", *_create_metrics(fn=1)),
                (0, "Z", *_create_metrics(fp=1))
            ], columns=("forecast_time", "sensor_id", "tp", "tn", "fp", "fn"))
        ),
    ])
    def test_calculate_detailed(self,
                                forecast_offsets: typing.List[int],
                                precip_types: typing.List[PrecipitationType],
                                observations: pandas.DataFrame,
                                forecast: pandas.DataFrame,
                                expected_metrics: pandas.DataFrame):
        worker = _create_worker(forecast_offsets=forecast_offsets,
                                precip_types=precip_types,
                                threshold=0.1)

        result = worker._calculate(forecast_times=forecast_offsets,
                                   observations=observations,
                                   forecast=forecast)

        merged_result = pandas.merge(expected_metrics,
                                     result,
                                     left_on=["forecast_time", "sensor_id"],
                                     right_on=["forecast_time", "id"],
                                     suffixes=("_expected", "_result"))

        for metric in ["tp", "tn", "fp", "fn"]:
            assert (merged_result[f"{metric}_expected"] ==
                    merged_result[f"{metric}_result"]).all(), f"Mismatch found in {metric}"

    @pytest.mark.parametrize("forecast_offsets, precip_types, observations, forecast, expected_metrics", [
        (
            [0, 600, 1200, 1800],
            [PrecipitationType.RAIN],
            _create_observations([
                ("sensor_1", 10.0, PrecipitationType.RAIN.value, _timestamp(0)),
                ("sensor_2", 0.0, PrecipitationType.RAIN.value, _timestamp(0)),
                ("sensor_3", 10.0, PrecipitationType.RAIN.value, _timestamp(0))
            ]),
            _create_forecast([
                # 1 TP, 1 FP -> 0.5 precision, 1.0 recall
                ("sensor_1", 10.0, PrecipitationType.RAIN.value, _timestamp(0), 600),
                ("sensor_2", 10.0, PrecipitationType.RAIN.value, _timestamp(0), 600),

                # 1 FN, 1 FP -> 0.0 precision, 0.0 recall
                ("sensor_1", 0.0, PrecipitationType.RAIN.value, _timestamp(0), 1200),
                ("sensor_2", 10.0, PrecipitationType.RAIN.value, _timestamp(0), 1200),

                # 1 TP, 1 FP, 1 FN -> 0.5 precision, 0.5 recall
                ("sensor_1", 10.0, PrecipitationType.RAIN.value, _timestamp(0), 1800),
                ("sensor_2", 10.0, PrecipitationType.RAIN.value, _timestamp(0), 1800),
                ("sensor_3", 0.0, PrecipitationType.RAIN.value, _timestamp(0), 1800)
            ]),
            _create_metrics_result(data=(
                (600, 0.5, 1.0, fscore(0.5, 1.0)),
                (1200, 0.0, 0.0, fscore(0.0, 0.0)),
                (1800, 0.5, 0.5, fscore(0.5, 0.5))
            ), columns=("forecast_time", "precision", "recall", "fscore"))
        ),
        (
            [0],
            [PrecipitationType.RAIN],
            _create_observations([
                ("X", 10.0, PrecipitationType.RAIN.value, _timestamp(0)),
                ("Y", 0.0, PrecipitationType.UNKNOWN.value, _timestamp(0)),
                ("Z", 10.0, PrecipitationType.SNOW.value, _timestamp(0))
            ]),
            _create_forecast([
                # 1 TP, 2 TN -> 1.0 precision, 1.0 recall
                ("X", 10.0, PrecipitationType.RAIN.value, _timestamp(0), 0),
                ("Y", 0.0, PrecipitationType.UNKNOWN.value, _timestamp(0), 0),
                ("Z", 10.0, PrecipitationType.SNOW.value, _timestamp(0), 0)
            ]),
            _create_metrics_result(data=[
                (0, 1, 1, 1)
            ], columns=("forecast_time", "precision", "recall", "fscore"))
        ),
        (
            [0],
            [PrecipitationType.RAIN, PrecipitationType.SNOW],
            _create_observations([
                ("X", 10.0, PrecipitationType.SNOW.value, _timestamp(0)),
                ("Y", 0.0, PrecipitationType.UNKNOWN.value, _timestamp(0)),
                ("Z", 10.0, PrecipitationType.RAIN.value, _timestamp(0))
            ]),
            _create_forecast([
                # 2 TP, 1 TN -> 1.0 precision, 1.0 recall
                ("X", 10.0, PrecipitationType.RAIN.value, _timestamp(0), 0),
                ("Y", 0.0, PrecipitationType.MIX.value, _timestamp(0), 0),
                ("Z", 10.0, PrecipitationType.SNOW.value, _timestamp(0), 0)
            ]),
            _create_metrics_result(data=[
                (0, 1, 1, 1)
            ], columns=("forecast_time", "precision", "recall", "fscore"))
        ),
        (
            [0],
            [PrecipitationType.SNOW],
            _create_observations([
                ("X", 10.0, PrecipitationType.SNOW.value, _timestamp(0)),
                ("Y", 10.0, PrecipitationType.SNOW.value, _timestamp(0)),
                ("Z", 10.0, PrecipitationType.RAIN.value, _timestamp(0))
            ]),
            _create_forecast([
                # 1 TP, 1 FN, 1 FP -> 0.5 precision, 0.5 recall
                ("X", 10.0, PrecipitationType.SNOW.value, _timestamp(0), 0),
                ("Y", 10.0, PrecipitationType.RAIN.value, _timestamp(0), 0),
                ("Z", 10.0, PrecipitationType.SNOW.value, _timestamp(0), 0)
            ]),
            _create_metrics_result(data=[
                (0, 0.5, 0.5, fscore(0.5, 0.5))
            ], columns=("forecast_time", "precision", "recall", "fscore"))
        ),
    ])
    def test_precision_recall_fscore(self,
                                     forecast_offsets: typing.List[int],
                                     precip_types: typing.List[PrecipitationType],
                                     observations: pandas.DataFrame,
                                     forecast: pandas.DataFrame,
                                     expected_metrics: pandas.DataFrame):
        worker = _create_worker(forecast_offsets=forecast_offsets,
                                precip_types=precip_types,
                                threshold=0.1)

        result = worker._calculate(forecast_times=forecast_offsets,
                                   observations=observations,
                                   forecast=forecast)

        result = result.groupby(["forecast_time"])[["tp", "tn", "fp", "fn"]].sum().reset_index()
        result["precision"] = result[["tp", "fp"]].apply(lambda row: precision(row["tp"], row["fp"]), axis=1)
        result["recall"] = result[["tp", "fn"]].apply(lambda row: recall(row["tp"], row["fn"]), axis=1)
        result["fscore"] = result[["precision", "recall"]].apply(
            lambda row: fscore(row["precision"], row["recall"]), axis=1)

        merged_result = pandas.merge(expected_metrics, result, on="forecast_time", suffixes=("_expected", "_result"))
        for metric in ["recall", "precision", "fscore"]:
            assert (merged_result[f"{metric}_expected"] ==
                    merged_result[f"{metric}_result"]).all(), f"Mismatch found in {metric}"


class TestCalculateMetrics:
    @pytest.mark.parametrize("session_time_range, expected_time_range", [
        ((10, 3500), (0, 3600)),
        ((0, 3601), (0, 7200)),
        ((1, 3599), (0, 3600)),
        ((0, 3600), (0, 3600)),
        ((7300, 9700), (7200, 10800))
    ])
    @patch("metrics.session.Session.create_from_folder")
    def test_calc_sensors_range(self,
                                mock_session_create: any,
                                session_time_range: typing.Tuple[int, int],
                                expected_time_range: typing.Tuple[int, int]):

        mock_session_create.return_value = Session(session_path="test",
                                                   start_time=session_time_range[0],
                                                   end_time=session_time_range[1])

        calc = _create_calculate_metrics()

        assert calc._calc_sensors_range() == expected_time_range
