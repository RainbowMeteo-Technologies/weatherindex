import pytest

from forecast.providers.provider import BaseProvider
from forecast.providers.accuweather import AccuWeather
from forecast.sensor import Sensor
from unittest.mock import MagicMock


@pytest.fixture
def test_sensors():
    return [
        Sensor(id="test1", lon=10.0, lat=20.0, country="test_country"),
        Sensor(id="test2", lon=11.0, lat=21.0, country="test_country")
    ]


def test_accuweather_smoke(test_sensors):
    client = AccuWeather(sensors=test_sensors,
                         download_path="test_download_path",
                         token="test_token",
                         publisher=MagicMock())
    assert isinstance(client, AccuWeather)
    assert isinstance(client, BaseProvider)
    assert len(client.sensors) == 2
