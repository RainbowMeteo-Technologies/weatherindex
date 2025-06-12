import pytest

from forecast.providers.provider import BaseProvider
from forecast.providers.microsoft import Microsoft
from forecast.sensor import Sensor
from unittest.mock import MagicMock


@pytest.fixture
def test_sensors():
    return [
        Sensor(id="test1", lon=10.0, lat=20.0, country="test_country"),
        Sensor(id="test2", lon=11.0, lat=21.0, country="test_country")
    ]


def test_microsoft_smoke(test_sensors):
    client = Microsoft(sensors=test_sensors,
                       download_path="test_download_path",
                       client_id="test_client_id",
                       subscription_key="test_subscription_key",
                       publisher=MagicMock())
    assert isinstance(client, Microsoft)
    assert isinstance(client, BaseProvider)
    assert len(client.sensors) == 2
