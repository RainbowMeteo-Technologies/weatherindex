import pytest

from forecast.providers.provider import BaseProvider, BaseRateLimitedForecastInPointProvider
from forecast.providers.meteolibre import MeteoLibre
from forecast.sensor import Sensor
from unittest.mock import MagicMock


@pytest.fixture
def test_sensors():
    return [
        Sensor(id="test1", lon=10.0, lat=20.0, country="test_country"),
        Sensor(id="test2", lon=11.0, lat=21.0, country="test_country")
    ]


def test_meteolibre_smoke(test_sensors):
    client = MeteoLibre(sensors=test_sensors,
                        download_path="test_download_path",
                        publisher=MagicMock(),
                        qps=10.0)
    assert isinstance(client, MeteoLibre)
    assert isinstance(client, BaseProvider)
    assert isinstance(client, BaseRateLimitedForecastInPointProvider)
    assert len(client.sensors) == 2


def test_meteolibre_default_api_url(test_sensors):
    client = MeteoLibre(sensors=test_sensors,
                        download_path="test_download_path",
                        publisher=MagicMock(),
                        qps=10.0)
    assert "api.meteolibre.dev" in client.api_url
    assert "nowcast" not in client.api_url  # base URL, not full endpoint


def test_meteolibre_custom_api_url(test_sensors):
    custom_url = "https://my-custom-api.example.com"
    client = MeteoLibre(sensors=test_sensors,
                        download_path="test_download_path",
                        publisher=MagicMock(),
                        qps=10.0,
                        api_url=custom_url)
    assert client.api_url == custom_url
