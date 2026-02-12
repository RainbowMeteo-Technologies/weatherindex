import pytest

from forecast.providers.provider import BaseProvider
from forecast.providers.rainbow import Rainbow
from forecast.sensor import Sensor
from forecast.utils.req_interface import Response
from unittest.mock import MagicMock, patch


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


@pytest.mark.asyncio
@pytest.mark.parametrize("response, is_ok", [

    (
        Response(status=200, payload="some response"),
        True
    ),
    (
        Response(status=200, payload=b"some response"),
        True
    ),
    (
        Response(status=200, payload=""),
        False
    ),
    (
        Response(status=200, payload=b""),
        False
    ),

])
async def test_rainbow_get_json_forecast_in_point(test_sensors, response, is_ok):
    client = Rainbow(sensors=test_sensors,
                     token="test_token",
                     download_path="test_download_path",
                     publisher=MagicMock())
    with patch.object(client, "_native_get", return_value=response):
        assert (await client.get_json_forecast_in_point(0, 0)).ok == is_ok
