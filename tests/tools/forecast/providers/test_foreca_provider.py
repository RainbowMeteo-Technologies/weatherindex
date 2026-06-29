import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from forecast.providers.foreca import Foreca
from forecast.providers.provider import BaseProvider, BaseRateLimitedForecastInPointProvider
from forecast.sensor import Sensor
from forecast.utils.req_interface import Response


@pytest.fixture
def test_sensors():
    return [
        Sensor(id="test1", lon=10.0, lat=20.0, country="test_country"),
        Sensor(id="test2", lon=11.0, lat=21.0, country="test_country")
    ]


def test_foreca_smoke(test_sensors):
    client = Foreca(sensors=test_sensors,
                    token="test_token",
                    qps=1.0,
                    download_path="test_download_path",
                    publisher=MagicMock())
    assert isinstance(client, Foreca)
    assert isinstance(client, BaseProvider)
    assert isinstance(client, BaseRateLimitedForecastInPointProvider)
    assert len(client.sensors) == 2
    assert client.token == "test_token"


def test_foreca_default_product(test_sensors):
    client = Foreca(sensors=test_sensors,
                    token="test_token",
                    qps=1.0,
                    download_path="test_download_path",
                    publisher=MagicMock())
    assert client.endpoint == Foreca._API_PRODUCT_ENDPOINT_MAPPING["nowcast-long"]


def test_foreca_nowcast_short_product(test_sensors):
    client = Foreca(sensors=test_sensors,
                    token="test_token",
                    product="nowcast-short",
                    qps=1.0,
                    download_path="test_download_path",
                    publisher=MagicMock())
    assert client.endpoint == Foreca._API_PRODUCT_ENDPOINT_MAPPING["nowcast-short"]


def test_foreca_api_products():
    assert "nowcast-short" in Foreca.API_PRODUCTS
    assert "nowcast-long" in Foreca.API_PRODUCTS


@pytest.mark.asyncio
@patch.object(Foreca, "_native_get", new_callable=AsyncMock)
async def test_get_json_forecast_in_point_success(mock_get, test_sensors):
    mock_get.return_value = Response(status=200, payload=b'{"test": "data"}')

    client = Foreca(sensors=test_sensors,
                    token="test_token",
                    qps=1.0,
                    download_path="test_download_path",
                    publisher=MagicMock())
    response = await client.get_json_forecast_in_point(lon=10.0, lat=20.0)

    assert response.ok is True
    assert response.status == 200

    payload = json.loads(response.payload)
    assert "position" in payload
    assert "payload" in payload
    assert payload["position"] == {"lon": 10.0, "lat": 20.0}
    assert payload["payload"] == {"test": "data"}


@pytest.mark.asyncio
@patch.object(Foreca, "_native_get", new_callable=AsyncMock)
async def test_get_json_forecast_in_point_failure(mock_get, test_sensors):
    mock_get.return_value = Response(status=500)

    client = Foreca(sensors=test_sensors,
                    token="test_token",
                    qps=1.0,
                    download_path="test_download_path",
                    publisher=MagicMock())
    response = await client.get_json_forecast_in_point(lon=10.0, lat=20.0)

    assert response.ok is False
    assert response.status == 500


@pytest.mark.asyncio
@patch.object(Foreca, "_native_get", new_callable=AsyncMock)
async def test_rate_limit_aware_get_success(mock_get, test_sensors):
    mock_get.return_value = Response(status=200, payload=b'{"data": "value"}')

    client = Foreca(sensors=test_sensors,
                    token="test_token",
                    qps=1.0,
                    download_path="test_download_path",
                    publisher=MagicMock())
    response = await client.rate_limit_aware_get(
        url="https://example.com/forecast",
        headers={"Authorization": "Bearer test_token"}
    )

    assert response.ok is True
    assert response.status == 200
    mock_get.assert_called_once()


@pytest.mark.asyncio
@patch.object(Foreca, "_native_get", new_callable=AsyncMock)
async def test_rate_limit_aware_get_429_no_retry_after(mock_get, test_sensors):
    mock_get.return_value = Response(status=429, headers={})

    client = Foreca(sensors=test_sensors,
                    token="test_token",
                    qps=1.0,
                    download_path="test_download_path",
                    publisher=MagicMock())
    response = await client.rate_limit_aware_get(
        url="https://example.com/forecast",
        headers={"Authorization": "Bearer test_token"}
    )

    assert response.status == 429
    assert response.ok is False
    mock_get.assert_called_once()


@pytest.mark.asyncio
@patch("asyncio.sleep", new_callable=AsyncMock)
@patch.object(Foreca, "_native_get", new_callable=AsyncMock)
async def test_rate_limit_aware_get_429_with_retry_after(mock_get, mock_sleep, test_sensors):
    mock_get.side_effect = [
        Response(status=429, headers={"retry-after": 5.0}),
        Response(status=200, payload=b'{"data": "value"}'),
    ]

    client = Foreca(sensors=test_sensors,
                    token="test_token",
                    qps=1.0,
                    download_path="test_download_path",
                    publisher=MagicMock())
    response = await client.rate_limit_aware_get(
        url="https://example.com/forecast",
        headers={"Authorization": "Bearer test_token"}
    )

    assert response.ok is True
    assert response.status == 200
    mock_sleep.assert_called_once_with(5.0)
    assert mock_get.call_count == 2
