import pytest

from forecast.client.base import SensorClientBase
from forecast.client.myradar import MyRadar
from forecast.sensor import Sensor


@pytest.fixture
def test_sensors():
    return [
        Sensor(id="test1", lon=10.0, lat=20.0, country="test_country"),
        Sensor(id="test2", lon=11.0, lat=21.0, country="test_country")
    ]


def test_myradar_smoke(test_sensors):
    client = MyRadar(sensors=test_sensors, sub_key="test_sub_key")
    assert isinstance(client, MyRadar)
    assert isinstance(client, SensorClientBase)
    assert len(client.sensors) == 2
