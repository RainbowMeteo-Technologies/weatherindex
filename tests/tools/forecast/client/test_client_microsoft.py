import pytest
from unittest.mock import AsyncMock, patch
import json

from forecast.client.base import SensorClientBase
from forecast.client.microsoft import Microsoft
from forecast.req_interface import Response
from forecast.sensor import Sensor


@pytest.fixture
def test_sensors():
    return [
        Sensor(id="test1", lon=10.0, lat=20.0, country="test_country"),
        Sensor(id="test2", lon=11.0, lat=21.0, country="test_country")
    ]


def test_microsoft_smoke(test_sensors):
    client = Microsoft(sensors=test_sensors, client_id="test_client_id", subscription_key="test_subscription_key")
    assert isinstance(client, Microsoft)
    assert isinstance(client, SensorClientBase)
    assert len(client.sensors) == 2


@pytest.mark.asyncio
@patch.object(Microsoft, "_native_get", new_callable=AsyncMock)
async def test_get_json_forecast_in_point(mock_get, test_sensors):
    mock_response = Response(
        status=200,
        payload="{\"test\": \"data\"}"
    )
    mock_get.return_value = mock_response

    client = Microsoft(sensors=test_sensors, client_id="test_client_id", subscription_key="test_subscription_key")
    response = await client._get_json_forecast_in_point(lon=10.0, lat=20.0)

    assert response.status == 200
    assert response.ok is True

    # Parse the response payload to verify its structure
    payload = json.loads(response.payload)
    assert "position" in payload
    assert "payload" in payload
    assert payload["position"] == {"lon": 10.0, "lat": 20.0}
    assert payload["payload"] == {"test": "data"}
