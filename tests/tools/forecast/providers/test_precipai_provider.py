import io
import json
import numpy as np
import os
import pandas as pd
import pytest
import xarray as xr
import zipfile

from datetime import datetime, timezone
from forecast.providers.precipai import PrecipAi
from forecast.publishers.publisher import Publisher
from forecast.sensor import Sensor


HOUR = 3600
DAY = 24 * HOUR
STEP = 300
LEADS = 24

# the archive grid of the fixture: 0.01° cells, centers from 42.995°N down and from -100.995°E up,
# 300 × 300 cells, so the sensors fall into different 128 × 128 chunks
LAT_CENTERS = np.round(42.995 - 0.01 * np.arange(300), 3)
LON_CENTERS = np.round(-100.995 + 0.01 * np.arange(300), 3)

# a run of the downloader at 2026-10-21 12:00 UTC picks up the runs initialized in (10:00, 11:00] the day before
RUN_TIME = int(datetime(2026, 10, 21, 12, tzinfo=timezone.utc).timestamp())
FIRST_INIT_TIME = RUN_TIME - DAY - 2 * HOUR  # 2026-10-20 10:00 UTC

SNAPSHOT_ID = "Z71K4JNX2X3PP48H66YG"

# sensor -> (lon, lat, row, column of the nearest cell)
SENSORS = {
    "uscrn_00001": (-100.9913, 42.9961, 0, 0),          # inside the first chunk
    "uscrn_00002": (-99.5049, 41.2552, 174, 149),       # second chunk in both directions
    "uscrn_00003": (-98.0001, 40.0051, 299, 299),       # the last cell, near the grid edge
}
OUTSIDE_SENSOR = Sensor(id="uscrn_26494", lon=-149.9, lat=61.2, country="USA")   # Alaska, outside the grid


def _rate(init_index: int, lead_index: int, row: int, column: int) -> float:
    """A distinct value per run, lead and cell: 0.01 mm/h steps, as stored by the archive (uint16 × 0.01)"""
    return round(init_index * 10 + lead_index + (row * 300 + column) % 7 * 0.01, 2)


def _sensors() -> list[Sensor]:
    return [Sensor(id=sensor_id, lon=lon, lat=lat, country="USA")
            for sensor_id, (lon, lat, _, _) in SENSORS.items()] + [OUTSIDE_SENSOR]


def _write_archive(path: str, init_times: list[int], lon_centers: np.ndarray = LON_CENTERS) -> str:
    """A local Zarr store laid out like the precip.ai archive group `mrms_native`, longitudes in -180..180
    unless given otherwise"""
    init_index, lead_index, row, column = np.meshgrid(np.arange(len(init_times)), np.arange(LEADS),
                                                      np.arange(len(LAT_CENTERS)), np.arange(len(LON_CENTERS)),
                                                      indexing="ij")
    rate = np.round(init_index * 10 + lead_index + (row * 300 + column) % 7 * 0.01, 2)  # `_rate` of every cell
    rate[:, :, 0, 1] = np.nan  # no data next to the first sensor

    ds = xr.Dataset(
        {"precipitation_rate": (("init_time", "lead_time", "latitude", "longitude"), rate)},
        coords={"init_time": pd.to_datetime(init_times, unit="s"),
                "lead_time": pd.to_timedelta(np.arange(LEADS) * STEP, unit="s"),
                "latitude": LAT_CENTERS,
                "longitude": lon_centers})
    ds.to_zarr(path, group="mrms_native", consolidated=False, mode="w",
               encoding={"precipitation_rate": {"chunks": (1, LEADS, 128, 128)}})
    return path


class RecordingPublisher(Publisher):
    """Keeps the content of every published archive"""

    def __init__(self):
        self.archives: dict[str, dict[str, bytes]] = {}

    async def publish(self, snapshot_path: str) -> None:
        with zipfile.ZipFile(snapshot_path) as zip_file:
            self.archives[os.path.basename(snapshot_path)] = {name: zip_file.read(name)
                                                              for name in zip_file.namelist()}


@pytest.fixture
def archive_path(tmp_path) -> str:
    # runs every 5 minutes over 3 hours, the last ones are not available to the first run yet
    init_times = list(range(FIRST_INIT_TIME, FIRST_INIT_TIME + 3 * HOUR, STEP))
    return _write_archive(str(tmp_path / "archive"), init_times)


def _provider(tmp_path, archive_path: str, publisher: Publisher) -> PrecipAi:
    def open_archive() -> tuple[xr.Dataset, str]:
        return xr.open_zarr(archive_path, group="mrms_native", consolidated=False), SNAPSHOT_ID

    return PrecipAi(sensors=_sensors(),
                    publisher=publisher,
                    download_path=str(tmp_path / "download"),
                    open_archive=open_archive)


def _points(archive: dict[str, bytes], init_time: int) -> pd.DataFrame:
    return pd.read_csv(io.BytesIO(archive[f"{init_time}/precipai.csv"]))


@pytest.mark.asyncio
async def test_run_writes_the_runs_that_became_available_since_the_previous_run(tmp_path, archive_path):
    publisher = RecordingPublisher()
    provider = _provider(tmp_path, archive_path, publisher)

    await provider.download(RUN_TIME)

    # initialized in (RUN_TIME - 25h, RUN_TIME - 24h]
    expected = range(RUN_TIME - DAY - HOUR + STEP, RUN_TIME - DAY + 1, STEP)
    assert sorted(publisher.archives) == [f"{init_time}.zip" for init_time in expected]


@pytest.mark.asyncio
async def test_next_run_writes_only_newer_runs_including_late_ones_after_a_restart(tmp_path):
    archive_path = str(tmp_path / "archive")
    # the 2026-10-20 12:00 UTC run is not published yet at the first run
    _write_archive(archive_path, list(range(FIRST_INIT_TIME, RUN_TIME - DAY, STEP)))
    first = RecordingPublisher()
    await _provider(tmp_path, archive_path, first).download(RUN_TIME)

    _write_archive(archive_path, list(range(FIRST_INIT_TIME, FIRST_INIT_TIME + 4 * HOUR, STEP)))
    second = RecordingPublisher()
    # a new provider: the downloader was restarted between the runs
    await _provider(tmp_path, archive_path, second).download(RUN_TIME + HOUR)

    assert sorted(first.archives) == [f"{t}.zip" for t in range(RUN_TIME - DAY - HOUR + STEP, RUN_TIME - DAY, STEP)]
    assert sorted(second.archives) == [f"{t}.zip" for t in range(RUN_TIME - DAY, RUN_TIME - DAY + HOUR + 1, STEP)]


@pytest.mark.asyncio
async def test_repeated_run_writes_nothing(tmp_path, archive_path):
    await _provider(tmp_path, archive_path, RecordingPublisher()).download(RUN_TIME)

    publisher = RecordingPublisher()
    await _provider(tmp_path, archive_path, publisher).download(RUN_TIME)

    assert publisher.archives == {}


class FailingPublisher(RecordingPublisher):
    """Fails to publish the archive run initialized at `failing_init_time`"""

    def __init__(self, failing_init_time: int):
        super().__init__()
        self.failing_init_time = failing_init_time

    async def publish(self, snapshot_path: str) -> None:
        if os.path.basename(snapshot_path) == f"{self.failing_init_time}.zip":
            raise ConnectionError("S3 is unavailable")
        await super().publish(snapshot_path)


@pytest.mark.asyncio
async def test_run_after_a_failed_publish_retries_from_the_failed_archive_run(tmp_path, archive_path):
    failing_init_time = RUN_TIME - DAY - 30 * 60
    failing = FailingPublisher(failing_init_time)
    await _provider(tmp_path, archive_path, failing).download(RUN_TIME)

    publisher = RecordingPublisher()
    await _provider(tmp_path, archive_path, publisher).download(RUN_TIME + HOUR)

    published_before_failure = range(RUN_TIME - DAY - HOUR + STEP, failing_init_time, STEP)
    assert sorted(failing.archives) == [f"{t}.zip" for t in published_before_failure]
    assert sorted(publisher.archives)[0] == f"{failing_init_time}.zip"


@pytest.mark.asyncio
async def test_unreachable_archive_publishes_nothing(tmp_path):
    def unreachable() -> tuple[xr.Dataset, str]:
        raise ConnectionError("api.precip.ai is unavailable")

    publisher = RecordingPublisher()
    provider = PrecipAi(sensors=_sensors(), publisher=publisher, download_path=str(tmp_path / "download"),
                        open_archive=unreachable)

    assert await provider.download(RUN_TIME) == []
    assert publisher.archives == {}


@pytest.mark.asyncio
async def test_snapshot_has_the_nearest_cell_of_every_sensor_at_every_lead(tmp_path, archive_path):
    publisher = RecordingPublisher()
    await _provider(tmp_path, archive_path, publisher).download(RUN_TIME)

    init_time = RUN_TIME - DAY  # 2026-10-20 12:00 UTC, the 25th run of the archive
    init_index = (init_time - FIRST_INIT_TIME) // STEP
    points = _points(publisher.archives[f"{init_time}.zip"], init_time)

    assert list(points.columns) == ["id", "lon", "lat", "grid_lon", "grid_lat", "lead_time", "precipitation_rate"]
    # the cell next to the first sensor has no data, the Alaska sensor is outside the grid
    assert set(points["id"]) == set(SENSORS)
    for sensor_id, (lon, lat, row, column) in SENSORS.items():
        rows = points[points["id"] == sensor_id].sort_values("lead_time")
        assert rows["lead_time"].tolist() == [lead * STEP for lead in range(LEADS)]
        assert rows["precipitation_rate"].tolist() == pytest.approx(
            [_rate(init_index, lead, row, column) for lead in range(LEADS)])
        assert (rows["lon"] == lon).all() and (rows["lat"] == lat).all()
        assert (rows["grid_lon"] == LON_CENTERS[column]).all() and (rows["grid_lat"] == LAT_CENTERS[row]).all()


@pytest.mark.asyncio
@pytest.mark.parametrize("lon_centers", [LON_CENTERS, np.round(LON_CENTERS + 360, 3)], ids=["-180..180", "0..360"])
async def test_sensors_find_their_cells_in_both_longitude_conventions(tmp_path, lon_centers):
    archive_path = _write_archive(str(tmp_path / "archive"), [RUN_TIME - DAY], lon_centers=lon_centers)
    publisher = RecordingPublisher()
    await _provider(tmp_path, archive_path, publisher).download(RUN_TIME)

    points = _points(publisher.archives[f"{RUN_TIME - DAY}.zip"], RUN_TIME - DAY)

    assert set(points["id"]) == set(SENSORS)
    for sensor_id, (lon, lat, row, column) in SENSORS.items():
        rows = points[points["id"] == sensor_id]
        expected_rates = [_rate(0, lead, row, column) for lead in range(2)]
        assert rows.sort_values("lead_time")["precipitation_rate"].tolist()[:2] == pytest.approx(expected_rates)
        # grid longitudes are reported in the convention of the sensors
        assert rows["grid_lon"].to_numpy() == pytest.approx(LON_CENTERS[column])


@pytest.mark.asyncio
async def test_snapshot_records_the_archive_snapshot_id(tmp_path, archive_path):
    publisher = RecordingPublisher()
    await _provider(tmp_path, archive_path, publisher).download(RUN_TIME)

    init_time = RUN_TIME - DAY
    meta = json.loads(publisher.archives[f"{init_time}.zip"][f"{init_time}/snapshot.json"])

    assert meta["snapshot_id"] == SNAPSHOT_ID
    assert meta["init_time"] == init_time
