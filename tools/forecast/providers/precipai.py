import asyncio
import functools
import json
import numpy as np
import os
import pandas as pd
import shutil
import xarray as xr

from concurrent.futures import ThreadPoolExecutor
from forecast.providers.provider import BaseProvider
from forecast.sensor import Sensor
from forecast.utils.time import Timestamp, time_to_next_run
from rich.console import Console
from typing import Callable


console = Console()

# https://api-docs.precip.ai/nowcast-archive
ARCHIVE_URL = "https://api.precip.ai/icechunk/precip-rate-v4/5min"
ARCHIVE_BRANCH = "main"
ARCHIVE_GROUP = "mrms_native"
ARCHIVE_VARIABLE = "precipitation_rate"  # liquid-water-equivalent mm/h

# a run is published once its init time is at least 24 hours old
AVAILABILITY_DELAY = 24 * 3600

# spatial chunk size of the archive, used when the store does not report it
CHUNK_SIZE = 128
# chunks read in parallel
READ_WORKERS = 16

# content of a published snapshot `<init time>.zip`
POINTS_FILE_NAME = "precipai.csv"
# init time of the last published run, kept in the download path to resume after a restart
STATE_FILE_NAME = "last_init_time"
SNAPSHOT_FILE_NAME = "snapshot.json"
# `lon`, `lat`: sensor location, `grid_lon`, `grid_lat`: center of its nearest cell,
# `lead_time`: seconds after the init time, `precipitation_rate`: mm/h
POINTS_COLUMNS = ["id", "lon", "lat", "grid_lon", "grid_lat", "lead_time", "precipitation_rate"]


def open_icechunk_archive(url: str = ARCHIVE_URL) -> tuple[xr.Dataset, str]:
    """Opens the archive at the head of its branch, returns the dataset and the Icechunk snapshot id read"""
    import icechunk  # needs Python 3.12, imported here so the other providers do not depend on it

    repo = icechunk.Repository.open(icechunk.http_storage(url))
    session = repo.readonly_session(ARCHIVE_BRANCH)
    return xr.open_zarr(session.store, group=ARCHIVE_GROUP, consolidated=False), session.snapshot_id


class PrecipAi(BaseProvider):
    """
    precip.ai nowcast archive (Icechunk) at the sensors' points.

    Every run picks up the archive runs initialized after the last written one (and at least 24 hours ago),
    and publishes one `<init time>.zip` per archive run.
    """

    def __init__(self,
                 sensors: list[Sensor],
                 archive_url: str = ARCHIVE_URL,
                 open_archive: Callable[[], tuple[xr.Dataset, str]] | None = None,
                 frequency: int = 3600,
                 **kwargs):
        """
        Parameters
        ----------
        archive_url : str
            URL of the Icechunk repository
        open_archive : Callable[[], tuple[xr.Dataset, str]] | None
            Opens the archive group, returns the dataset and the snapshot id read. Opens `archive_url`
            with Icechunk by default
        """
        super().__init__(frequency=frequency, **kwargs)
        self.sensors = sensors
        self._archive_url = archive_url
        self._open_archive = open_archive or functools.partial(open_icechunk_archive, archive_url)

    async def run(self):
        while True:
            time_to_sleep = time_to_next_run(self._frequency) + self._delay
            console.log(f"Next archive runs will be picked up in {time_to_sleep} seconds.")
            await asyncio.sleep(time_to_sleep)

            start_time = Timestamp.get_current()
            await self.download(Timestamp.floor(start_time, self._frequency))
            console.log(f"It took {Timestamp.get_current() - start_time} seconds to download data")

    async def download(self, timestamp: int) -> list[int]:
        """
        Publishes the archive runs that became available since the previous run.

        Parameters
        ----------
        timestamp : int
            The time of the run

        Returns
        -------
        list[int]
            Init times of the published archive runs. A failure stops the run, the next run retries
            from the failed archive run
        """
        try:
            ds, snapshot_id = await asyncio.to_thread(self._open_archive)
        except Exception as ex:
            console.log(f"Wasn't able to open the precip.ai archive {self._archive_url}: {ex}")
            return []

        # the last written run, or the runs that became available within the last period on the first start
        last = self._read_last_init_time()
        if last is None:
            last = timestamp - AVAILABILITY_DELAY - self._frequency
        available = timestamp - AVAILABILITY_DELAY
        init_times = [t for t in _init_timestamps(ds) if last < t <= available]

        cells = _nearest_cells(ds, self.sensors)
        console.log(f"{len(cells)} of {len(self.sensors)} sensors are inside the archive grid, "
                    f"{len(init_times)} archive runs to download (snapshot {snapshot_id})")

        published = []
        for init_time in init_times:
            try:
                await self._publish_run(ds, snapshot_id, init_time, cells)
            except Exception as ex:
                console.log(f"Wasn't able to publish the archive run {init_time}: {ex}")
                break
            finally:
                shutil.rmtree(self.snapshot_path(init_time), ignore_errors=True)
                if os.path.exists(f"{self.snapshot_path(init_time)}.zip"):
                    os.remove(f"{self.snapshot_path(init_time)}.zip")

            self._write_last_init_time(init_time)
            published.append(init_time)

        return published

    async def _publish_run(self, ds: xr.Dataset, snapshot_id: str, init_time: int, cells: pd.DataFrame):
        """Publishes `<init time>.zip` with the points of the archive run and the snapshot id they were read from"""
        snapshot_path = self.snapshot_path(init_time)
        shutil.rmtree(snapshot_path, ignore_errors=True)
        os.makedirs(snapshot_path, exist_ok=False)

        points = await asyncio.to_thread(_read_points, ds, init_time, cells)
        points.to_csv(os.path.join(snapshot_path, POINTS_FILE_NAME), index=False)
        with open(os.path.join(snapshot_path, SNAPSHOT_FILE_NAME), "w") as f:
            json.dump({"init_time": init_time,
                       "snapshot_id": snapshot_id,
                       "archive": self._archive_url,
                       "group": ARCHIVE_GROUP,
                       "variable": ARCHIVE_VARIABLE}, f)

        shutil.make_archive(base_name=snapshot_path,
                            format="zip",
                            root_dir=self._download_path,
                            base_dir=str(init_time))
        await self._publisher.publish(snapshot_path=f"{snapshot_path}.zip")

    async def fetch_job(self, timestamp: int):
        raise NotImplementedError("PrecipAi publishes one snapshot per archive run, see `download`")

    @property
    def _state_path(self) -> str:
        return os.path.join(self._download_path, STATE_FILE_NAME)

    def _read_last_init_time(self) -> int | None:
        if not os.path.exists(self._state_path):
            return None
        with open(self._state_path) as f:
            return int(f.read().strip())

    def _write_last_init_time(self, init_time: int):
        with open(self._state_path, "w") as f:
            f.write(str(init_time))


def _init_timestamps(ds: xr.Dataset) -> list[int]:
    return [int(t) for t in ds["init_time"].values.astype("datetime64[s]").astype("int64")]


def _nearest_index(centers: np.ndarray, values: list[float]) -> np.ndarray:
    """Positions of the nearest cell centers, -1 for values outside the grid (beyond half a cell)"""
    half_cell = abs(float(centers[1] - centers[0])) / 2
    return pd.Index(centers).get_indexer(values, method="nearest", tolerance=half_cell + 1e-9)


def _nearest_cells(ds: xr.Dataset, sensors: list[Sensor]) -> pd.DataFrame:
    """The nearest grid cell (`row`, `column`) of every sensor inside the grid"""
    latitudes = ds["latitude"].values
    longitudes = ds["longitude"].values
    cells = pd.DataFrame({"id": [s.id for s in sensors],
                          "lon": [s.lon for s in sensors],
                          "lat": [s.lat for s in sensors],
                          "row": _nearest_index(latitudes, [s.lat for s in sensors]),
                          "column": _nearest_index(longitudes, [s.lon for s in sensors])})
    cells = cells[(cells["row"] >= 0) & (cells["column"] >= 0)].reset_index(drop=True)
    cells["grid_lon"] = longitudes[cells["column"]]
    cells["grid_lat"] = latitudes[cells["row"]]
    return cells


def _read_points(ds: xr.Dataset, init_time: int, cells: pd.DataFrame) -> pd.DataFrame:
    """
    Values of every lead of the archive run at the cells, read once per 128 × 128 chunk holding cells.
    Cells without data (NaN) are left out.
    """
    rate = ds[ARCHIVE_VARIABLE].sel(init_time=np.datetime64(init_time, "s"))
    lead_times = ds["lead_time"].values.astype("timedelta64[s]").astype("int64")
    chunk_size = (ds[ARCHIVE_VARIABLE].encoding.get("chunks") or (None, None, CHUNK_SIZE, CHUNK_SIZE))[-2:]

    blocks = cells.groupby([cells["row"] // chunk_size[0], cells["column"] // chunk_size[1]])

    def read_block(block: tuple[tuple[int, int], pd.DataFrame]) -> pd.DataFrame:
        (block_row, block_column), block_cells = block
        row0, column0 = block_row * chunk_size[0], block_column * chunk_size[1]
        values = rate.isel(latitude=slice(row0, row0 + chunk_size[0]),
                           longitude=slice(column0, column0 + chunk_size[1])).values
        # leads × cells
        values = values[:, block_cells["row"].to_numpy() - row0, block_cells["column"].to_numpy() - column0]
        points = block_cells.loc[block_cells.index.repeat(len(lead_times))].reset_index(drop=True)
        points["lead_time"] = np.tile(lead_times, len(block_cells))
        points["precipitation_rate"] = values.T.reshape(-1)
        return points

    with ThreadPoolExecutor(max_workers=READ_WORKERS) as executor:
        frames = list(executor.map(read_block, blocks))

    if len(frames) == 0:
        return pd.DataFrame(columns=POINTS_COLUMNS)
    points = pd.concat(frames)[POINTS_COLUMNS]
    return points.dropna(subset=["precipitation_rate"]).sort_values(["id", "lead_time"]).reset_index(drop=True)
