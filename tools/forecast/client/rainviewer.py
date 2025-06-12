import aiohttp
import asyncio
import datetime
import json
import os

from concurrent.futures import ProcessPoolExecutor
from forecast.client.base import ClientBase
from forecast.req_interface import Response
from forecast.sensor import Sensor
from itertools import product
from rich.console import Console
from tqdm import tqdm
from typing_extensions import override  # for python <3.12


console = Console()


BATCH_SIZE = 12
DOWNLOAD_TRY_NUM = 5
DOWNLOAD_TRY_SLEEP = 1
MAX_CONNECTIONS_PER_SESSION = 10
MAX_WAIT_TIME = 5 * 60


def get_current_time() -> int:
    return int(datetime.datetime.now().timestamp())


async def _try_download_file(session: aiohttp.ClientSession, url: str) -> Response:
    sleep_time = DOWNLOAD_TRY_SLEEP
    resp = Response()
    for attempt in range(DOWNLOAD_TRY_NUM):
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    return Response(status=response.status,
                                    payload=(await response.read()))
                else:
                    resp = Response(status=response.status)
        except Exception as ex:
            console.log(f"Wasn't able to download `{url}`. "
                        f"Attempt {attempt + 1} of {DOWNLOAD_TRY_NUM}. "
                        f"Next try in {sleep_time} seconds. "
                        f"Exception: {str(ex)}")

            await asyncio.sleep(sleep_time)
            sleep_time *= 2

    return resp


def _download_tiles_batch(jobs: list[tuple[str, str]]) -> list[Response]:

    async def download_one_tile(session: aiohttp.ClientSession, url: str, file_path: str) -> Response:
        resp = await _try_download_file(session, url)
        if resp.ok:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "wb") as file:
                file.write(resp.payload)
                return resp

        console.log(f"Wasn't able to download tile `{url}`")
        return resp

    async def download_batch() -> list[Response]:
        connector = aiohttp.TCPConnector(limit=MAX_CONNECTIONS_PER_SESSION)
        async with aiohttp.ClientSession(connector=connector) as session:
            run_jobs = []

            for job in jobs:
                url, file_path = job
                run_jobs.append(download_one_tile(session, url, file_path))

            return await asyncio.gather(*run_jobs)

    return asyncio.run(download_batch())


class RainViewer(ClientBase):
    TILE_SIZE = 256
    METADATA_RETRY_DELAY = 15

    def __init__(self, token: str, zoom: int):
        super().__init__()
        self.token = token
        self.zoom = zoom

    async def _get_metadata(self) -> dict[object, object] | None:
        url = f"https://api.rainviewer.com/private/{self.token}/weather-maps.json"

        resp = await self._native_get(url=url)
        if resp.ok:
            return json.loads(resp.payload)

        return None

    @override
    async def get_forecast(self,
                           download_path: str,
                           process_num: int | None = None,
                           chunk_size: int | None = None):
        snapshot_timestamp = int(os.path.basename(download_path))

        snapshot_available = False
        metadata = None
        current_observation = None

        while not snapshot_available:
            metadata = await self._get_metadata()

            if metadata is None:
                return

            current_observation = max(metadata["radar"]["past"], key=lambda x: x["time"])
            if current_observation["time"] == snapshot_timestamp:
                snapshot_available = True
            else:
                if get_current_time() > snapshot_timestamp + MAX_WAIT_TIME:
                    console.log(f"Snapshot {snapshot_timestamp} is not available")
                    return

                console.log(f"Waiting for snapshot {snapshot_timestamp}...")
                await asyncio.sleep(RainViewer.METADATA_RETRY_DELAY)

        available_frames = [current_observation] + metadata["radar"]["nowcast"]
        available_frames.sort(key=lambda x: x["time"])

        # 7 frames are available for each tile: current observation and 6 nowcasts
        assert len(available_frames) == 7
        assert metadata is not None

        jobs = []
        for tile_x, tile_y in product(range(0, 2 ** self.zoom), range(0, 2 ** self.zoom)):
            tile_rel_path = os.path.join(str(self.zoom), str(tile_x), f"{tile_y}.png")

            mask_tile_url = os.path.join(str(metadata["host"]),
                                         "v2", "coverage", "0",
                                         str(RainViewer.TILE_SIZE),
                                         str(self.zoom),
                                         str(tile_x),
                                         str(tile_y),
                                         "0", "0_0.png")
            mask_tile_path = os.path.join(download_path, "_mask", tile_rel_path)

            jobs.append((mask_tile_url, mask_tile_path))

            for frame_info in available_frames:
                delta_time = (frame_info["time"] - snapshot_timestamp) // 60  # minutes

                map_tile_url = os.path.join(f"{metadata['host']}{frame_info['path']}",
                                            str(RainViewer.TILE_SIZE),
                                            str(self.zoom),
                                            str(tile_x),
                                            str(tile_y),
                                            "0", "0_0.png")
                map_tile_path = os.path.join(download_path, "_map", f"t{str(delta_time)}", tile_rel_path)

                jobs.append((map_tile_url, map_tile_path))

        console.log(f"Downloading {len(jobs)} tiles")

        responses = await self.execute_with_batches(args=jobs,
                                                    chunk_func=_download_tiles_batch,
                                                    chunk_size=BATCH_SIZE,
                                                    process_num=process_num)

        # Count successful responses
        valid_results = sum([1 for resp in responses if resp.ok])
        console.log(f"Downloaded {valid_results} tiles")
        console.log(f"Errors: {len(jobs) - valid_results}")

        self.save_fetching_report(folder=download_path,
                                  targets=[job[0] for job in jobs],
                                  statuses=[resp.ok for resp in responses],
                                  codes=[resp.status for resp in responses])
