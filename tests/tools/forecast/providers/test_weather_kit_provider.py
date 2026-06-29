import pytest

from forecast.providers.provider import BaseProvider
from forecast.providers.weather_kit import WeatherKit, datasets_from_forecast_types
from forecast.sensor import Sensor
from forecast.utils.req_interface import Response
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def test_sensors():
    return [
        Sensor(id="test1", lon=10.0, lat=20.0, country="test_country"),
        Sensor(id="test2", lon=11.0, lat=21.0, country="test_country")
    ]


def test_weather_kit_smoke(test_sensors):
    client = WeatherKit(sensors=test_sensors,
                        config_path="config.json",
                        forecast_types=["hour"],
                        download_path="test_download_path",
                        publisher=MagicMock())
    assert isinstance(client, WeatherKit)
    assert isinstance(client, BaseProvider)
    assert len(client.sensors) == 2


def test_datasets_from_forecast_types_all():
    datasets = datasets_from_forecast_types(["hour", "day", "week"])
    assert "forecastNextHour" in datasets
    assert "forecastHourly" in datasets
    assert "forecastDaily" in datasets


def test_datasets_from_forecast_types_partial():
    assert datasets_from_forecast_types(["hour"]) == ["forecastNextHour"]
    assert datasets_from_forecast_types(["day"]) == ["forecastHourly"]
    assert datasets_from_forecast_types(["week"]) == ["forecastDaily"]


def test_datasets_from_forecast_types_empty():
    assert datasets_from_forecast_types([]) == []


@pytest.mark.asyncio
@patch.object(WeatherKit, "_native_get", new_callable=AsyncMock)
async def test_get_json_forecast_in_point_success(mock_get, test_sensors):
    mock_get.return_value = Response(status=200, payload=b'{"test": "data"}')

    client = WeatherKit(sensors=test_sensors,
                        config_path="config.json",
                        forecast_types=["hour"],
                        download_path="test_download_path",
                        publisher=MagicMock())
    client.token = "test_token"
    response = await client.get_json_forecast_in_point(lon=10.0, lat=20.0)

    assert response.ok is True
    assert response.status == 200
    assert response.payload == b'{"test": "data"}'


@pytest.mark.asyncio
@patch.object(WeatherKit, "_native_get", new_callable=AsyncMock)
async def test_get_json_forecast_in_point_failure(mock_get, test_sensors):
    mock_get.return_value = Response(status=401)

    client = WeatherKit(sensors=test_sensors,
                        config_path="config.json",
                        forecast_types=["hour"],
                        download_path="test_download_path",
                        publisher=MagicMock())
    client.token = "test_token"
    response = await client.get_json_forecast_in_point(lon=10.0, lat=20.0)

    assert response.ok is False
    assert response.status == 401
