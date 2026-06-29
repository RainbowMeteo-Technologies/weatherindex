import json
import pytest

from forecast.providers.provider import BaseProvider
from forecast.providers.weather_company import WeatherCompany
from forecast.sensor import Sensor
from forecast.utils.req_interface import Response
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def test_sensors():
    return [
        Sensor(id="test1", lon=10.0, lat=20.0, country="test_country"),
        Sensor(id="test2", lon=11.0, lat=21.0, country="test_country")
    ]


def test_weather_company_smoke(test_sensors):
    for product_name in WeatherCompany.PRODUCT_NAMES:
        client = WeatherCompany(sensors=test_sensors, token="test_token",
                                download_path="test_download_path",
                                product_name=product_name,
                                publisher=MagicMock())
        assert isinstance(client, WeatherCompany)
        assert isinstance(client, BaseProvider)
        assert len(client.sensors) == 2


@pytest.mark.asyncio
@patch.object(WeatherCompany, "_native_get", new_callable=AsyncMock)
async def test_get_json_forecast_in_point_success(mock_get, test_sensors):
    mock_get.return_value = Response(status=200, payload=b'{"test": "data"}')

    client = WeatherCompany(sensors=test_sensors,
                            token="test_token",
                            product_name="forecast-15-minute",
                            download_path="test_download_path",
                            publisher=MagicMock())
    response = await client.get_json_forecast_in_point(lon=10.0, lat=20.0)

    assert response.ok is True
    assert response.status == 200

    payload = json.loads(response.payload)
    assert payload["position"] == {"lon": 10.0, "lat": 20.0}
    assert payload["product_name"] == "forecast-15-minute"
    assert payload["payload"] == {"test": "data"}


@pytest.mark.asyncio
@patch.object(WeatherCompany, "_native_get", new_callable=AsyncMock)
async def test_get_json_forecast_in_point_error_in_body(mock_get, test_sensors):
    error_body = {"errors": [{"code": "MGL-0001"}], "metadata": {"status_code": 404}}
    mock_get.return_value = Response(status=200, payload=json.dumps(error_body).encode())

    client = WeatherCompany(sensors=test_sensors,
                            token="test_token",
                            product_name="forecast-15-minute",
                            download_path="test_download_path",
                            publisher=MagicMock())
    response = await client.get_json_forecast_in_point(lon=10.0, lat=20.0)

    assert response.status == 404


@pytest.mark.asyncio
@patch.object(WeatherCompany, "_native_get", new_callable=AsyncMock)
async def test_get_json_forecast_in_point_failure(mock_get, test_sensors):
    mock_get.return_value = Response(status=500)

    client = WeatherCompany(sensors=test_sensors,
                            token="test_token",
                            product_name="forecast-15-minute",
                            download_path="test_download_path",
                            publisher=MagicMock())
    response = await client.get_json_forecast_in_point(lon=10.0, lat=20.0)

    assert response.ok is False
    assert response.status == 500
