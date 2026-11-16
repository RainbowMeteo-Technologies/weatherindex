import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from forecast.providers.google import Google
from forecast.providers.provider import BaseProvider, BaseRateLimitedForecastInPointProvider
from forecast.sensor import Sensor
from forecast.utils.req_interface import Response


@pytest.fixture
def test_sensors():
    return [
        Sensor(id="test1", lon=10.0, lat=20.0, country="test_country"),
        Sensor(id="test2", lon=11.0, lat=21.0, country="test_country")
    ]


def _make_client(sensors, **kwargs) -> Google:
    return Google(sensors=sensors,
                  token="test_token",
                  qps=1.0,
                  download_path="test_download_path",
                  publisher=MagicMock(),
                  **kwargs)


def test_google_smoke(test_sensors):
    client = _make_client(test_sensors)
    assert isinstance(client, Google)
    assert isinstance(client, BaseProvider)
    assert isinstance(client, BaseRateLimitedForecastInPointProvider)
    assert len(client.sensors) == 2
    assert client.token == "test_token"
    assert client.page_size == 30


def test_google_custom_page_size(test_sensors):
    client = _make_client(test_sensors, page_size=60)
    assert client.page_size == 60


@pytest.mark.asyncio
@patch.object(Google, "_native_get", new_callable=AsyncMock)
async def test_get_json_forecast_in_point_success(mock_get, test_sensors):
    mock_get.return_value = Response(status=200, payload=b'{"test": "data"}')

    client = _make_client(test_sensors)
    response = await client.get_json_forecast_in_point(lon=10.0, lat=20.0)

    assert response.ok is True
    assert response.status == 200

    payload = json.loads(response.payload)
    assert "position" in payload
    assert "payload" in payload
    assert payload["position"] == {"lon": 10.0, "lat": 20.0}
    assert payload["payload"] == {"test": "data"}

    mock_get.assert_called_once()
    _, kwargs = mock_get.call_args
    assert kwargs["url"] == "https://weather.googleapis.com/v1/forecast/minutes:lookup"
    assert kwargs["params"] == {
        "key": "test_token",
        "location.latitude": "20.0",
        "location.longitude": "10.0",
        "unitsSystem": "METRIC",
        "pageSize": "30",
    }


@pytest.mark.asyncio
@patch.object(Google, "_native_get", new_callable=AsyncMock)
async def test_get_json_forecast_in_point_failure(mock_get, test_sensors):
    mock_get.return_value = Response(status=500)

    client = _make_client(test_sensors)
    response = await client.get_json_forecast_in_point(lon=10.0, lat=20.0)

    assert response.ok is False
    assert response.status == 500
    mock_get.assert_called_once()


@pytest.mark.asyncio
@patch.object(Google, "_native_get", new_callable=AsyncMock)
async def test_rate_limit_aware_get_429_no_retry_after(mock_get, test_sensors):
    mock_get.return_value = Response(status=429, headers={})

    client = _make_client(test_sensors)
    response = await client.get_json_forecast_in_point(lon=10.0, lat=20.0)

    assert response.status == 429
    assert response.ok is False
    mock_get.assert_called_once()


@pytest.mark.asyncio
@patch("asyncio.sleep", new_callable=AsyncMock)
@patch.object(Google, "_native_get", new_callable=AsyncMock)
async def test_rate_limit_aware_get_429_with_retry_after(mock_get, mock_sleep, test_sensors):
    mock_get.side_effect = [
        Response(status=429, headers={"Retry-After": "5"}),
        Response(status=200, payload=b'{"data": "value"}'),
    ]

    client = _make_client(test_sensors)
    response = await client.get_json_forecast_in_point(lon=10.0, lat=20.0)

    assert response.ok is True
    assert response.status == 200
    mock_sleep.assert_called_once_with(5.0)
    assert mock_get.call_count == 2
    assert json.loads(response.payload)["payload"] == {"data": "value"}
