import pytest

from forecast.providers.provider import BaseProvider
from forecast.providers.vaisala import Vaisala
from forecast.sensor import Sensor
from unittest.mock import MagicMock


@pytest.fixture
def test_sensors():
    return [
        Sensor(id="test1", lon=10.0, lat=20.0, country="test_country"),
        Sensor(id="test2", lon=11.0, lat=21.0, country="test_country")
    ]


def test_vaisala_smoke(test_sensors):
    client = Vaisala(sensors=test_sensors,
                     client_id="test_client_id",
                     client_secret="test_client_secret",
                     download_path="test_download_path",
                     publisher=MagicMock())
    assert isinstance(client, Vaisala)
    assert isinstance(client, BaseProvider)
    assert len(client.sensors) == 2
