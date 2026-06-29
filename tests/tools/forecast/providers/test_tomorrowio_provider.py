import json
import pytest

from forecast.providers.provider import BaseProvider
from forecast.providers.tomorrowio import TomorrowIo
from forecast.sensor import Sensor
from forecast.utils.req_interface import Response
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def test_sensors():
    return [
        Sensor(id="test1", lon=10.0, lat=20.0, country="test_country"),
        Sensor(id="test2", lon=11.0, lat=21.0, country="test_country")
    ]


def test_tomorrowio_smoke(test_sensors):
    client = TomorrowIo(sensors=test_sensors,
                        forecast_type="type",
                        token="token",
                        download_path="test_download_path",
                        publisher=MagicMock())
    assert isinstance(client, TomorrowIo)
    assert isinstance(client, BaseProvider)
    assert len(client.sensors) == 2


@pytest.mark.asyncio
@patch.object(TomorrowIo, "_native_get", new_callable=AsyncMock)
async def test_get_json_forecast_in_point_hour(mock_get, test_sensors):
    mock_get.return_value = Response(status=200, payload=b'{"test": "data"}')

    client = TomorrowIo(sensors=test_sensors,
                        token="test_token",
                        forecast_type="hour",
                        download_path="test_download_path",
                        publisher=MagicMock())
    response = await client.get_json_forecast_in_point(lon=10.0, lat=20.0)

    assert response.ok is True
    payload = json.loads(response.payload)
    assert payload["position"] == {"lon": 10.0, "lat": 20.0}
    assert payload["payload"] == {"test": "data"}
    mock_get.assert_called_once()


@pytest.mark.asyncio
@patch.object(TomorrowIo, "_native_post", new_callable=AsyncMock)
async def test_get_json_forecast_in_point_6hours(mock_post, test_sensors):
    mock_post.return_value = Response(status=200, payload=b'{"test": "data"}')

    client = TomorrowIo(sensors=test_sensors,
                        token="test_token",
                        forecast_type="6hours",
                        download_path="test_download_path",
                        publisher=MagicMock())
    response = await client.get_json_forecast_in_point(lon=10.0, lat=20.0)

    assert response.ok is True
    payload = json.loads(response.payload)
    assert payload["position"] == {"lon": 10.0, "lat": 20.0}
    assert payload["payload"] == {"test": "data"}
    mock_post.assert_called_once()


@pytest.mark.asyncio
async def test_get_json_forecast_in_point_unknown_type(test_sensors):
    client = TomorrowIo(sensors=test_sensors,
                        token="test_token",
                        forecast_type="unknown",
                        download_path="test_download_path",
                        publisher=MagicMock())
    response = await client.get_json_forecast_in_point(lon=10.0, lat=20.0)

    assert response.ok is False
    assert response.status == 0


@pytest.mark.asyncio
@patch.object(TomorrowIo, "_native_get", new_callable=AsyncMock)
async def test_get_json_forecast_in_point_failure(mock_get, test_sensors):
    mock_get.return_value = Response(status=500)

    client = TomorrowIo(sensors=test_sensors,
                        token="test_token",
                        forecast_type="hour",
                        download_path="test_download_path",
                        publisher=MagicMock())
    response = await client.get_json_forecast_in_point(lon=10.0, lat=20.0)

    assert response.ok is False
    assert response.status == 500
