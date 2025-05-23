import pytest

from forecast.client.base import SensorClientBase
from forecast.client.weather_company import WeatherCompany
from forecast.sensor import Sensor


@pytest.fixture
def test_sensors():
    return [
        Sensor(id="test1", lon=10.0, lat=20.0, country="test_country"),
        Sensor(id="test2", lon=11.0, lat=21.0, country="test_country")
    ]


def test_weather_company_smoke(test_sensors):
    client = WeatherCompany(sensors=test_sensors, token="test_token")
    assert isinstance(client, WeatherCompany)
    assert isinstance(client, SensorClientBase)
    assert len(client.sensors) == 2
