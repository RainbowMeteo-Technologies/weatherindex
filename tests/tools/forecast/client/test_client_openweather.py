import pytest

from forecast.client.base import SensorClientBase
from forecast.client.openweather import OpenWeather
from forecast.sensor import Sensor


@pytest.fixture
def test_sensors():
    return [
        Sensor(id="test1", lon=10.0, lat=20.0, country="test_country"),
        Sensor(id="test2", lon=11.0, lat=21.0, country="test_country")
    ]


def test_openweather_smoke(test_sensors):
    client = OpenWeather(sensors=test_sensors, token="test_token")
    assert isinstance(client, OpenWeather)
    assert isinstance(client, SensorClientBase)
    assert len(client.sensors) == 2
