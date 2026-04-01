import os
import functools
import pandas
import pytest
import typing

from metrics.session import Session
from metrics.utils.precipitation import PrecipitationType

from unittest.mock import MagicMock, patch

from tests.utils.metrics.calc import create_worker, create_observations, create_forecast, create_metrics, create_metrics_result, timestamp, create_calculate_metrics


class TestWorker:
    @patch("metrics.calc.events.Session.create_from_folder")
    @patch("metrics.calc.events.pandas.read_parquet")
    def test_worker_smoke_run(self, read_parquet_mock, session_create_mock):
        forecast_manager_mock = MagicMock()
        forecast_manager_cls_mock = MagicMock()
        forecast_manager_cls_mock.return_value = forecast_manager_mock

        worker = create_worker(forecast_manager_cls=forecast_manager_cls_mock)
        worker._get_sensor_file_list = MagicMock()
        worker._get_sensor_file_list.side_effect = ["1.parquet", "2.parquet"]

        observation_columns = ["id", "precip_type", "precip_rate", "timestamp"]
        read_parquet_mock.side_effect = [pandas.DataFrame(columns=observation_columns),
                                         pandas.DataFrame(columns=observation_columns)]

        forecast_columns = ["id", "forecast_time", "precip_type", "precip_rate", "timestamp"]
        forecast_manager_mock.load_forecast.side_effect = [pandas.DataFrame(columns=forecast_columns),
                                                           pandas.DataFrame(columns=forecast_columns)]

        worker._dump_frame = MagicMock()

        worker.run()

        worker._dump_frame.assert_called_once()

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

        worker = create_worker()
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

        worker = create_worker()
        result = worker._align_time_column(data=data, column_name=column_name, period=period)

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
            create_observations([
                ("sensor_tp", 10.0, PrecipitationType.RAIN.value, timestamp(7800, 60)),
                ("sensor_tn", 0.0, PrecipitationType.UNKNOWN.value, timestamp(7800, 100)),
                ("sensor_fp", 0.0, PrecipitationType.UNKNOWN.value, timestamp(7800, 1750)),
                ("sensor_fn", 10.0, PrecipitationType.RAIN.value, timestamp(7800, 3540)),
            ]),
            # forecast
            create_forecast([
                ("sensor_tp", 10.0, PrecipitationType.RAIN.value, timestamp(7800, 60), 60),
                ("sensor_tn", 0.0, PrecipitationType.RAIN.value, timestamp(7800, 100), 100),
                ("sensor_fp", 10.0, PrecipitationType.RAIN.value, timestamp(7800, 1700), 1700),
                ("sensor_fn", 0.0, PrecipitationType.RAIN.value, timestamp(7800, 3550), 3550)
            ]),
            # expected_metrics
            create_metrics_result(data=(
                (600, *create_metrics(tp=1, tn=1)),
                (1800, *create_metrics(fp=1)),
                (3600, *create_metrics(fn=1))
            ), columns=("forecast_time", "tp", "tn", "fp", "fn"))
        ),
        # time ceil
        # this test checks that events are grouped correctly by range (0; 10m] (excluding zero)
        (
            # forecast_times
            [0, 600, 1200],
            # observations
            create_observations([
                # 0 minutes
                ("sensor_00:00", 10.0, PrecipitationType.RAIN.value, timestamp(0, -1)),
                # 10 minutes
                ("sensor_00:01", 10.0, PrecipitationType.RAIN.value, timestamp(0, 1)),
                ("sensor_09:59", 10.0, PrecipitationType.RAIN.value, timestamp(0, 599)),
                ("sensor_10:00", 10.0, PrecipitationType.RAIN.value, timestamp(0, 600)),
                # 20 minutes
                ("sensor_10:01", 10.0, PrecipitationType.RAIN.value, timestamp(0, 601)),
                ("sensor_20:00", 10.0, PrecipitationType.RAIN.value, timestamp(0, 1200)),
            ]),
            # forecast
            create_forecast([
                # 0 minutes
                ("sensor_00:00", 10.0, PrecipitationType.RAIN.value, timestamp(0, -1), 0),
                # 10 minutes
                ("sensor_00:01", 10.0, PrecipitationType.RAIN.value, timestamp(0, 1), 600),
                ("sensor_09:59", 10.0, PrecipitationType.RAIN.value, timestamp(0, 599), 600),
                ("sensor_10:00", 10.0, PrecipitationType.RAIN.value, timestamp(0, 600), 600),
                # 20 minutes
                ("sensor_10:01", 10.0, PrecipitationType.RAIN.value, timestamp(0, 601), 1200),
                ("sensor_20:00", 10.0, PrecipitationType.RAIN.value, timestamp(0, 1200), 1200),
            ]),
            # expected_metrics
            create_metrics_result(data=(
                (0, *create_metrics(tp=1)),
                (600, *create_metrics(tp=3)),
                (1200, *create_metrics(tp=2))
            ), columns=("forecast_time", "tp", "tn", "fp", "fn"))
        ),
        # do not group different precip_type
        # this test checks that only rain precipitation used for metrics calculation
        (
            # forecast_times
            [0, 600],
            # observations
            create_observations([
                # 0 minutes
                ("sensor_00:00", 10.0, PrecipitationType.RAIN.value, timestamp(0)),
                # 10 minutes
                ("sensor_00:01", 10.0, PrecipitationType.SNOW.value, timestamp(1)),
            ]),
            # forecast
            create_forecast([
                # 0 minutes
                ("sensor_00:00", 10.0, PrecipitationType.RAIN.value, timestamp(0), 0),
                # 10 minutes
                ("sensor_00:01", 10.0, PrecipitationType.RAIN.value, timestamp(1), 1),
            ]),
            # expected_metrics
            create_metrics_result(data=(
                (0, *create_metrics(tp=1)),
                (600, *create_metrics(fp=1))
            ), columns=("forecast_time", "tp", "tn", "fp", "fn"))
        ),
        # Observation duplicates
        (
            # forecast_times
            [0],
            # observations
            create_observations([
                # 0 minutes
                ("sensor_00:00", 10.0, PrecipitationType.RAIN.value, timestamp(0)),
                ("sensor_00:00", 10.0, PrecipitationType.RAIN.value, timestamp(0)),
            ]),
            # forecast
            create_forecast([
                # 0 minutes
                ("sensor_00:00", 10.0, PrecipitationType.RAIN.value, timestamp(0), 0),
            ]),
            # expected_metrics
            create_metrics_result(data=(
                (0, *create_metrics(tp=1)),
            ), columns=("forecast_time", "tp", "tn", "fp", "fn"))
        ),
        # Maximum observation in 10 minutes. Checks that maximum value from the sensor was used
        (
            # forecast_times
            [0],
            # observations
            create_observations([
                # 0 minutes
                ("sensor_10:00", 0.0, PrecipitationType.RAIN.value, timestamp(1)),
                ("sensor_10:00", 0.0, PrecipitationType.RAIN.value, timestamp(2 * 60)),
                ("sensor_10:00", 10.0, PrecipitationType.RAIN.value, timestamp(5 * 60)),
            ]),
            # forecast
            create_forecast([
                # 0 minutes
                ("sensor_10:00", 10.0, PrecipitationType.RAIN.value, timestamp(10 * 60), 0),
            ]),
            # expected_metrics
            create_metrics_result(data=(
                (0, *create_metrics(tp=1)),
            ), columns=("forecast_time", "tp", "tn", "fp", "fn"))
        ),
    ])
    def test_calculate(self,
                       forecast_times: typing.List[int],
                       observations: pandas.DataFrame,
                       forecast: pandas.DataFrame,
                       expected_metrics: pandas.DataFrame):

        worker = create_worker(forecast_offsets=forecast_times)

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
                                mock_session_create: typing.Any,
                                session_time_range: typing.Tuple[int, int],
                                expected_time_range: typing.Tuple[int, int]):

        mock_session_create.return_value = Session(session_path="test",
                                                   start_time=session_time_range[0],
                                                   end_time=session_time_range[1])

        calc = create_calculate_metrics()

        assert calc._calc_sensors_range() == expected_time_range

    @patch("metrics.calc.events.read_selected_sensors", return_value=pandas.DataFrame({"id": ["S0", "S1", "S2"]}))
    @patch("metrics.session.Session.create_from_folder", return_value=Session(session_path="session_path",
                                                                              start_time=0,
                                                                              end_time=3600))
    def test_collect_jobs(self, mock_session_create, mock_read_sensors):
        calc = create_calculate_metrics()

        collected_jobs = calc.collect_jobs()

        assert len(collected_jobs) > 0

        for job in collected_jobs:
            assert isinstance(job, functools.partial)
            assert set(job.keywords) == set(["params"])
            assert job.args == ()
