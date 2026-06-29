import json
import pytest

from forecast.providers.provider import BaseProvider
from forecast.providers.vaisala import Vaisala
from forecast.sensor import Sensor
from forecast.utils.req_interface import Response
from unittest.mock import AsyncMock, MagicMock, patch


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


@pytest.mark.asyncio
@patch.object(Vaisala, "_native_get", new_callable=AsyncMock)
async def test_get_json_forecast_in_point_success(mock_get, test_sensors):
    mock_get.return_value = Response(status=200, payload=b'{"test": "data"}')

    client = Vaisala(sensors=test_sensors,
                     client_id="test_client_id",
                     client_secret="test_client_secret",
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
@patch.object(Vaisala, "_native_get", new_callable=AsyncMock)
async def test_get_json_forecast_in_point_failure(mock_get, test_sensors):
    mock_get.return_value = Response(status=500)

    client = Vaisala(sensors=test_sensors,
                     client_id="test_client_id",
                     client_secret="test_client_secret",
                     download_path="test_download_path",
                     publisher=MagicMock())
    response = await client.get_json_forecast_in_point(lon=10.0, lat=20.0)

    assert response.ok is False
    assert response.status == 500


@pytest.mark.asyncio
@patch.object(Vaisala, "_native_get", new_callable=AsyncMock)
async def test_rate_limit_aware_get_success(mock_get, test_sensors):
    mock_get.return_value = Response(status=200, payload=b'{"data": "value"}')

    client = Vaisala(sensors=test_sensors,
                     client_id="test_client_id",
                     client_secret="test_client_secret",
                     download_path="test_download_path",
                     publisher=MagicMock())
    response = await client.rate_limit_aware_get(url="https://example.com/forecast")

    assert response.ok is True
    assert response.status == 200
    mock_get.assert_called_once()


@pytest.mark.asyncio
@patch.object(Vaisala, "_native_get", new_callable=AsyncMock)
async def test_rate_limit_aware_get_429_no_header(mock_get, test_sensors):
    mock_get.return_value = Response(status=429, headers={})

    client = Vaisala(sensors=test_sensors,
                     client_id="test_client_id",
                     client_secret="test_client_secret",
                     download_path="test_download_path",
                     publisher=MagicMock())
    response = await client.rate_limit_aware_get(url="https://example.com/forecast")

    assert response.status == 429
    assert response.ok is False
    mock_get.assert_called_once()


@pytest.mark.asyncio
@patch("asyncio.sleep", new_callable=AsyncMock)
@patch.object(Vaisala, "_native_get", new_callable=AsyncMock)
async def test_rate_limit_aware_get_429_with_reset_header(mock_get, mock_sleep, test_sensors):
    mock_get.side_effect = [
        Response(status=429, headers={"x-ratelimit-reset-minute": "Mon, 01 Jan 2099 00:00:00 GMT"}),
        Response(status=200, payload=b'{"data": "value"}'),
    ]

    client = Vaisala(sensors=test_sensors,
                     client_id="test_client_id",
                     client_secret="test_client_secret",
                     download_path="test_download_path",
                     publisher=MagicMock())
    response = await client.rate_limit_aware_get(url="https://example.com/forecast")

    assert response.ok is True
    assert response.status == 200
    mock_sleep.assert_called_once()
    assert mock_get.call_count == 2
