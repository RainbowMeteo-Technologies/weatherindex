import pytest

from forecast.providers.provider import BaseProvider, BaseForecastInPointProvider
from forecast.providers.flashnet import FlashNet
from forecast.sensor import Sensor
from unittest.mock import MagicMock


@pytest.fixture
def test_sensors():
    return [
        Sensor(id="test1", lon=10.0, lat=20.0, country="test_country"),
        Sensor(id="test2", lon=11.0, lat=21.0, country="test_country")
    ]


def test_flashnet_smoke(test_sensors):
    client = FlashNet(sensors=test_sensors,
                      download_path="test_download_path",
                      publisher=MagicMock())
    assert isinstance(client, FlashNet)
    assert isinstance(client, BaseProvider)
    assert isinstance(client, BaseForecastInPointProvider)
    assert len(client.sensors) == 2


def test_flashnet_default_api_url(test_sensors):
    client = FlashNet(sensors=test_sensors,
                      download_path="test_download_path",
                      publisher=MagicMock())
    assert "benchmark-api" in client.api_url
    assert "nowcast" not in client.api_url  # base URL, not full endpoint


def test_flashnet_custom_api_url(test_sensors):
    custom_url = "https://my-custom-api.example.com"
    client = FlashNet(sensors=test_sensors,
                      download_path="test_download_path",
                      publisher=MagicMock(),
                      api_url=custom_url)
    assert client.api_url == custom_url
