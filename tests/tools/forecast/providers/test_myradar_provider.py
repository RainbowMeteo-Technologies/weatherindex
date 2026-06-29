import pytest

from forecast.providers.provider import BaseProvider
from forecast.providers.myradar import MyRadar
from forecast.sensor import Sensor
from forecast.utils.req_interface import Response
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def test_sensors():
    return [
        Sensor(id="test1", lon=10.0, lat=20.0, country="test_country"),
        Sensor(id="test2", lon=11.0, lat=21.0, country="test_country")
    ]


def test_myradar_smoke(test_sensors):
    client = MyRadar(sensors=test_sensors,
                     sub_key="test_sub_key",
                     download_path="test_download_path",
                     publisher=MagicMock())
    assert isinstance(client, MyRadar)
    assert isinstance(client, BaseProvider)
    assert len(client.sensors) == 2


@pytest.mark.asyncio
@patch.object(MyRadar, "_native_get", new_callable=AsyncMock)
async def test_get_json_forecast_in_point_success(mock_get, test_sensors):
    mock_get.return_value = Response(status=200, payload=b'{"test": "data"}')

    client = MyRadar(sensors=test_sensors,
                     sub_key="test_sub_key",
                     download_path="test_download_path",
                     publisher=MagicMock())
    response = await client.get_json_forecast_in_point(lon=10.0, lat=20.0)

    assert response.ok is True
    assert response.status == 200
    assert response.payload == b'{"test": "data"}'


@pytest.mark.asyncio
@patch.object(MyRadar, "_native_get", new_callable=AsyncMock)
async def test_get_json_forecast_in_point_failure(mock_get, test_sensors):
    mock_get.return_value = Response(status=500)

    client = MyRadar(sensors=test_sensors,
                     sub_key="test_sub_key",
                     download_path="test_download_path",
                     publisher=MagicMock())
    response = await client.get_json_forecast_in_point(lon=10.0, lat=20.0)

    assert response.ok is False
    assert response.status == 500
