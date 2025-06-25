import pytest

from forecast.providers.provider import BaseProvider
from forecast.providers.weather_kit import WeatherKit
from forecast.sensor import Sensor
from unittest.mock import MagicMock


@pytest.fixture
def test_sensors():
    return [
        Sensor(id="test1", lon=10.0, lat=20.0, country="test_country"),
        Sensor(id="test2", lon=11.0, lat=21.0, country="test_country")
    ]


def test_weather_kit_smoke(test_sensors):
    client = WeatherKit(sensors=test_sensors,
                        config_path="config.json",
                        forecast_type="hour",
                        download_path="test_download_path",
                        publisher=MagicMock())
    assert isinstance(client, WeatherKit)
    assert isinstance(client, BaseProvider)
    assert len(client.sensors) == 2
