import asyncio
import json
import os
import pytest

from forecast.client.base import ClientBase, SensorClientBase, batched
from forecast.sensor import Sensor
from typing import List


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


class DummySensorClient(SensorClientBase):
    async def _get_json_forecast_in_point(self, lon: float, lat: float):
        await asyncio.sleep(1)
        return json.dumps({"test": "data", "lon": lon, "lat": lat})


@pytest.mark.asyncio
async def test_sensor_client_base_forecast(tmp_path):

    sensors = [Sensor(id=f"test{ind}",
                      lon=10.0,
                      lat=20.0,
                      country="country") for ind in range(800)]

    client = DummySensorClient(sensors)

    download_dir = str(tmp_path)

    await client.get_forecast(download_dir, process_num=8)

    # Assert that each sensor produced a file with the expected contents
    for s in sensors:
        p = tmp_path / f"{s.id}.json"
        assert p.exists(), f"Missing output file for sensor {s.id}"
        data = json.loads(p.read_text())
        assert data == {"test": "data", "lon": s.lon, "lat": s.lat}
