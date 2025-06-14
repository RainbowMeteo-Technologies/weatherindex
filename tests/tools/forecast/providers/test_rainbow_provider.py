import pytest

from forecast.providers.provider import BaseProvider
from forecast.providers.rainbow import Rainbow
from forecast.sensor import Sensor
from unittest.mock import MagicMock


@pytest.fixture
def test_sensors():
    return [
        Sensor(id="test1", lon=10.0, lat=20.0, country="test_country"),
        Sensor(id="test2", lon=11.0, lat=21.0, country="test_country")
    ]


def test_rainbow_smoke(test_sensors):
    client = Rainbow(sensors=test_sensors,
                     token="test_token",
                     download_path="test_download_path",
                     publisher=MagicMock())
    assert isinstance(client, Rainbow)
    assert isinstance(client, BaseProvider)
    assert len(client.sensors) == 2
