import pandas
import pytest
import typing

from enum import Enum

from metrics.calc.forecast_manager import ForecastManager, DataVendor
from metrics.calc.forecast.provider import ForecastProvider
from metrics.data_vendor import BaseDataVendor
from metrics.session import Session


def _create_sensors_table(data: typing.List[any]) -> pandas.DataFrame:
    return pandas.DataFrame(columns=["id", "lon", "lat"], data=data)


def _create_precip_table(data: typing.List[any]) -> pandas.DataFrame:
    return pandas.DataFrame(columns=["id", "precip_rate", "precip_type", "timestamp"], data=data)


def _create_forecast_table(data: typing.List[any]) -> pandas.DataFrame:
    return pandas.DataFrame(columns=["id", "precip_rate", "precip_type", "timestamp", "forecast_time"], data=data)


class DummyProvider(ForecastProvider):
    def __init__(self, timestamp: int) -> None:
        self._timestamp = timestamp


class MockProvider(ForecastProvider):
    def __init__(self, timestamp: int, mock_data: pandas.DataFrame) -> None:
        self._timestamp = timestamp
        self._mock_data = mock_data

    def load(self, sensors_table: pandas.DataFrame) -> pandas.DataFrame:
        return self._mock_data


class TestForecastManager:

    def test_get_provider_for_timestamp(self):
        session = Session(session_path="test", start_time=0, end_time=3600)
        manager = ForecastManager(data_vendor=DataVendor.AccuWeather, session=session)

        def mock_create_data_provider(timestamp: int) -> ForecastProvider:
            return DummyProvider(timestamp=timestamp)

        manager._create_data_provider = mock_create_data_provider

        provider_600 = manager._get_provider_for_timestamp(snapshot_timestamp=600)
        cached_600 = manager._get_provider_for_timestamp(snapshot_timestamp=600)

        assert provider_600 is not None
        assert provider_600._timestamp == 600
        assert cached_600 is not None
        assert cached_600 is provider_600

        provider_1200 = manager._get_provider_for_timestamp(snapshot_timestamp=1200)
        assert provider_1200 is not None
        assert provider_1200._timestamp == 1200
        assert provider_1200 is not provider_600

    def test_create_data_provider_invalid(self):
        session = Session(session_path="test", start_time=0, end_time=3600)

        class UnsupportedDataVendor(BaseDataVendor, Enum):
            Test = "test"
        manager = ForecastManager(data_vendor=UnsupportedDataVendor.Test, session=session)

        with pytest.raises(ValueError):
            manager._create_data_provider(0)

    @pytest.mark.parametrize("time_range, sensors_table, provider_data, expected_data", [
        (
            # time_range
            (0, 600),
            # sensors_table
            _create_sensors_table(data=[("sensor_1", 23.34, 53.43)]),
            # provider_data
            {
                0: _create_precip_table(data=[("sensor_1", 10.0, 1, 30),
                                              ("sensor_2", 10.0, 2, 650)]),
                600: _create_precip_table(data=[("sensor_1", 10.0, 2, 650)])
            },
            # expected_data
            _create_forecast_table(data=[("sensor_1", 10.0, 1, 30, 30),
                                         ("sensor_1", 10.0, 2, 650, 50)])
        )
    ])
    def test_load_forecast(self,
                           time_range: typing.Tuple[int, int],
                           sensors_table: pandas.DataFrame,
                           provider_data: typing.Dict[int, pandas.DataFrame],
                           expected_data: pandas.DataFrame):
        """
        Parameters
        ----------
        time_range : Tuple[int, int]
            Time range in seconds to load forecast
        sensors_table : pandas.DataFrame
            Table of sensors to filter data
        provider_data : Dict[int, pandas.DataFrame]
            Dictionary where `key` - is a timestamp of mock data, `value` - is a mocked provider data
        expected_data : pandas.DataFrame
            Expected loaded data
        """

        session = Session(session_path="test", start_time=0, end_time=3600)
        manager = ForecastManager(data_vendor=DataVendor.AccuWeather, session=session)

        def mock_get_provider_for_timestamp(timestamp: int) -> ForecastProvider:
            return MockProvider(timestamp=timestamp, mock_data=provider_data[timestamp])

        manager._get_provider_for_timestamp = mock_get_provider_for_timestamp

        result = manager.load_forecast(time_rage=time_range, sensors_table=sensors_table)

        print(result)
        print(expected_data)

        pandas.testing.assert_frame_equal(result.reset_index(drop=True),
                                          expected_data.reset_index(drop=True),
                                          check_like=True)
