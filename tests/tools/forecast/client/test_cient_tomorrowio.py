import pytest

from forecast.client.base import SensorClientBase
from forecast.client.tomorrowio import TomorrowIo
from forecast.sensor import Sensor


@pytest.fixture
def test_sensors():
    return [
        Sensor(id="test1", lon=10.0, lat=20.0, country="test_country"),
        Sensor(id="test2", lon=11.0, lat=21.0, country="test_country")
    ]


def test_tomorrowio_smoke(test_sensors):
    client = TomorrowIo(sensors=test_sensors, forecast_type="type", token="token")
    assert isinstance(client, TomorrowIo)
    assert isinstance(client, SensorClientBase)
    assert len(client.sensors) == 2
