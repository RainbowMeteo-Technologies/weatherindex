import asyncio
import json
import os
import pytest

from forecast.providers.provider import BaseForecastInPointProvider, batched
from forecast.sensor import Sensor
from forecast.utils.constants import FETCHING_REPORT_NAME
from forecast.utils.req_interface import Response
from typing_extensions import override


@pytest.mark.parametrize("input_data,batch_size,expected", [
    # String tests
    ("ABCDEFG", 3, [['A', 'B', 'C'], ['D', 'E', 'F'], ['G']]),
    ("ABCDEF", 2, [['A', 'B'], ['C', 'D'], ['E', 'F']]),
    ("ABC", 1, [['A'], ['B'], ['C']]),
    ("", 3, []),

    # List tests
    ([1, 2, 3, 4, 5], 2, [[1, 2], [3, 4], [5]]),
    ([1, 2, 3], 3, [[1, 2, 3]]),
    ([1, 2, 3, 4], 4, [[1, 2, 3, 4]]),
    ([], 3, []),
])
def test_batched(input_data, batch_size, expected):
    result = list(batched(input_data, batch_size))
    assert result == expected


@pytest.mark.parametrize("batch_size", [0, -1, -5])
def test_batched_invalid_size(batch_size):
    with pytest.raises(ValueError, match="n must be at least one"):
        list(batched("ABC", batch_size))


class DummySensorProvider(BaseForecastInPointProvider):
    @override
    async def get_json_forecast_in_point(self, lon: float, lat: float) -> Response:
        await asyncio.sleep(1)
        return Response(
            status=200,
            payload=json.dumps({"test": "data", "lon": lon, "lat": lat})
        )


@pytest.mark.asyncio
async def test_sensor_provider_base_forecast(tmp_path):

    sensors = [Sensor(id=f"test{ind}",
                      lon=10.0,
                      lat=20.0,
                      country="country") for ind in range(800)]

    timestamp = 1718236800

    download_dir = str(tmp_path)

    snapshot_path = os.path.join(download_dir, str(timestamp))
    os.makedirs(snapshot_path, exist_ok=True)

    client = DummySensorProvider(sensors,
                                 download_path=download_dir,
                                 publisher=None,
                                 process_num=8,
                                 chunk_size=100)

    await client.fetch_job(timestamp=timestamp)

    # Assert that each sensor produced a file with the expected contents
    for s in sensors:
        p = tmp_path / str(timestamp) / f"{s.id}.json"
        assert p.exists(), f"Missing output file for sensor {s.id}"
        data = json.loads(p.read_text())
        assert data == {"test": "data", "lon": s.lon, "lat": s.lat}

    # Check if fetching report was created
    report_path = tmp_path / str(timestamp) / FETCHING_REPORT_NAME
    assert report_path.exists(), "Missing fetching report"
