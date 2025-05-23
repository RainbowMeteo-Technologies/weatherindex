import pytest

from forecast.client.base import SensorClientBase
from forecast.client.microsoft import Microsoft
from forecast.sensor import Sensor


@pytest.fixture
def test_sensors():
    return [
        Sensor(id="test1", lon=10.0, lat=20.0, country="test_country"),
        Sensor(id="test2", lon=11.0, lat=21.0, country="test_country")
    ]


def test_microsoft_smoke(test_sensors):
    client = Microsoft(sensors=test_sensors, client_id="test_client_id", subscription_key="test_subscription_key")
    assert isinstance(client, Microsoft)
    assert isinstance(client, SensorClientBase)
    assert len(client.sensors) == 2
