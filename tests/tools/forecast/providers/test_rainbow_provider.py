import pytest

from forecast.providers.provider import BaseProvider
from forecast.providers.rainbow import Rainbow
from forecast.sensor import Sensor
from forecast.utils.req_interface import Response
from unittest.mock import AsyncMock, MagicMock, patch


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


def test_rainbow_api_products():
    assert "nowcast-precip" in Rainbow.API_PRODUCTS
    assert "nowcast-precip-global" in Rainbow.API_PRODUCTS
    assert "forecast-weather" in Rainbow.API_PRODUCTS


def test_rainbow_default_product(test_sensors):
    client = Rainbow(sensors=test_sensors,
                     token="test_token",
                     download_path="test_download_path",
                     publisher=MagicMock())
    assert client.endpoint == Rainbow._API_PRODUCT_ENDPOINT_MAPPING["nowcast-precip"]


def test_rainbow_product_variants(test_sensors):
    for product in Rainbow.API_PRODUCTS:
        client = Rainbow(sensors=test_sensors,
                         token="test_token",
                         product=product,
                         download_path="test_download_path",
                         publisher=MagicMock())
        assert client.endpoint == Rainbow._API_PRODUCT_ENDPOINT_MAPPING[product]


@pytest.mark.asyncio
@patch.object(Rainbow, "_native_get", new_callable=AsyncMock)
async def test_get_json_forecast_in_point_success(mock_get, test_sensors):
    mock_get.return_value = Response(status=200, payload=b'{"test": "data"}')

    client = Rainbow(sensors=test_sensors,
                     token="test_token",
                     download_path="test_download_path",
                     publisher=MagicMock())
    response = await client.get_json_forecast_in_point(lon=10.0, lat=20.0)

    assert response.ok is True
    assert response.status == 200
    assert response.payload == b'{"test": "data"}'


@pytest.mark.asyncio
@patch.object(Rainbow, "_native_get", new_callable=AsyncMock)
async def test_get_json_forecast_in_point_failure(mock_get, test_sensors):
    mock_get.return_value = Response(status=500)

    client = Rainbow(sensors=test_sensors,
                     token="test_token",
                     download_path="test_download_path",
                     publisher=MagicMock())
    response = await client.get_json_forecast_in_point(lon=10.0, lat=20.0)

    assert response.ok is False
    assert response.status == 500
