import aiohttp
import asyncio
import datetime
import json
import os

from concurrent.futures import ProcessPoolExecutor
from itertools import product
from typing import List, Tuple
from tqdm import tqdm

from forecast.req_interface import RequestInterface

from rich.console import Console

console = Console()


BATCH_SIZE = 12
DOWNLOAD_TRY_NUM = 5
DOWNLOAD_TRY_SLEEP = 1
MAX_CONNECTIONS_PER_SESSION = 10
MAX_WAIT_TIME = 5 * 60


def get_current_time() -> int:
    return int(datetime.datetime.now().timestamp())


async def _try_download_file(session: aiohttp.ClientSession, url: str):
    sleep_time = DOWNLOAD_TRY_SLEEP
    for attempt in range(DOWNLOAD_TRY_NUM):
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.read()
        except Exception as ex:
            console.log(f"Wasn't able to download `{url}`. "
                        f"Attempt {attempt + 1} of {DOWNLOAD_TRY_NUM}. "
                        f"Next try in {sleep_time} seconds. "
                        f"Exception: {str(ex)}")

            await asyncio.sleep(sleep_time)
            sleep_time *= 2

    return None


def _download_tiles_batch(jobs: List[Tuple[str, str]]) -> int:

    async def download_one_tile(session: aiohttp.ClientSession, url: str, file_path: str) -> bool:
        data = await _try_download_file(session, url)
        if data is not None:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "wb") as file:
                file.write(data)
                return True

        console.log(f"Wasn't able to download tile `{url}`")
        return False

    async def download_batch() -> int:
        connector = aiohttp.TCPConnector(limit=MAX_CONNECTIONS_PER_SESSION)
        async with aiohttp.ClientSession(connector=connector) as session:
            run_jobs = []

            for job in jobs:
                url, file_path = job
                run_jobs.append(download_one_tile(session, url, file_path))

            results = await asyncio.gather(*run_jobs)

            errors_num = 0
            for res in results:
                if not res:
                    errors_num += 1

            return errors_num

    return asyncio.run(download_batch())


class RainViewer(RequestInterface):
    TILE_SIZE = 256
    METADATA_RETRY_DELAY = 15

    def __init__(self, token: str, zoom: int):
        self.token = token
        self.zoom = zoom

    def _get_metadata(self):
        url = f"https://api.rainviewer.com/private/{self.token}/weather-maps.json"

        data = self._native_get(url=url)
        if data is not None:
            payload = json.loads(data)

            return payload

        return None

    async def get_forecast(self, download_path: str, process_num: int = None):
        snapshot_timestamp = int(os.path.basename(download_path))

        snapshot_available = False
        metadata = None
        current_observation = None

        while not snapshot_available:
            metadata = self._get_metadata()

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

        jobs = []
        for tile_x, tile_y in product(range(0, 2 ** self.zoom), range(0, 2 ** self.zoom)):
            tile_rel_path = os.path.join(str(self.zoom), str(tile_x), f"{tile_y}.png")

            mask_tile_url = f"{metadata['host']}/v2/coverage/0/{RainViewer.TILE_SIZE}/{self.zoom}/{tile_x}/{tile_y}/0/0_0.png"
            mask_tile_path = os.path.join(download_path, "_mask", tile_rel_path)

            jobs.append((mask_tile_url, mask_tile_path))

            for frame_info in available_frames:
                delta_time = (frame_info["time"] - snapshot_timestamp) // 60  # minutes

                map_tile_url = f"{metadata['host']}{frame_info['path']}/{RainViewer.TILE_SIZE}/{self.zoom}/{tile_x}/{tile_y}/0/0_0.png"
                map_tile_path = os.path.join(download_path, "_map", f"t{str(delta_time)}", tile_rel_path)

                jobs.append((map_tile_url, map_tile_path))

        console.log(f"Downloading {len(jobs)} tiles")
        batches = [jobs[i:i + BATCH_SIZE] for i in range(0, len(jobs), BATCH_SIZE)]

        loop = asyncio.get_event_loop()

        with ProcessPoolExecutor(max_workers=process_num) as executor:
            tasks = [loop.run_in_executor(executor, _download_tiles_batch, batch) for batch in batches]
            errors_num = 0
            for task in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Downloading tiles"):
                result = await task
                errors_num += result

            console.log(f"Downloaded {len(jobs) - errors_num} tiles")
            console.log(f"Errors: {errors_num}")
