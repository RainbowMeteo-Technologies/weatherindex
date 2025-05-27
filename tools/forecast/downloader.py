import aioboto3
import asyncio
import os
import shutil
import typing

from datetime import datetime
from rich.console import Console
from urllib.parse import urlparse


console = Console()


def get_current_time() -> int:
    return int(datetime.now().timestamp())


def align_time(timestamp: int, period: int = 3600) -> int:
    return timestamp - (timestamp % period)


class ForecastDownloader:
    def __init__(self,
                 download_path: str,
                 s3_uri: str,
                 process_num: int,
                 download_period: int,
                 client_initializer: typing.Callable[[], typing.Any],
                 keep_local_snapshots: bool = False):
        self._download_path = download_path
        self._s3_uri = s3_uri
        self._process_num = process_num
        self._download_period = download_period
        self._client_initializer = client_initializer
        self._keep_local_snapshots = keep_local_snapshots
        self._last_upload = get_current_time()

    async def _upload_snapshot(self, snapshot_path: str):
        # Parse the URL
        parsed_url = urlparse(self._s3_uri)

        # Get the bucket name (netloc) and object key (path)
        bucket_name = parsed_url.netloc
        object_key = parsed_url.path[1:]

        upload_file_name = os.path.basename(snapshot_path)

        file_stats = os.stat(snapshot_path)
        console.log(f"Uploading size {file_stats.st_size / 1024 / 1024:0.2f} MB")

        async with aioboto3.Session().client("s3") as s3:
            await s3.upload_file(snapshot_path, bucket_name, object_key + upload_file_name)

    async def run(self, snapshots_to_download: typing.Optional[int] = None):
        def keep_running(downloaded_snapshots: int) -> bool:
            return snapshots_to_download is None or downloaded_snapshots < snapshots_to_download

        console.log(f"Start download sensors:\n"
                    f"- destination bucket: {self._s3_uri}\n")

        downloaded_snapshots = 0

        while keep_running(downloaded_snapshots):
            current_time = get_current_time()
            current_snapshot = align_time(current_time, period=self._download_period)
            next_snapshot = current_snapshot + self._download_period

            # wait download
            wait_time = next_snapshot - current_time
            console.log(f"Next download in {wait_time} seconds. Snapshot - {next_snapshot}")
            await asyncio.sleep(wait_time)

            self._last_upload = get_current_time()

            client = self._client_initializer()
            snapshot_path = os.path.join(self._download_path, str(next_snapshot))

            shutil.rmtree(snapshot_path, ignore_errors=True)
            os.makedirs(snapshot_path, exist_ok=False)

            await client.get_forecast(download_path=snapshot_path,
                                      process_num=self._process_num)

            # compress
            shutil.make_archive(base_name=snapshot_path,
                                format="zip",
                                root_dir=self._download_path,
                                base_dir=str(next_snapshot))
            archive_path = f"{snapshot_path}.zip"

            if self._s3_uri is not None:
                console.log(f"Uploading snapshot {next_snapshot} to S3")
                await self._upload_snapshot(snapshot_path=archive_path)

            downloaded_snapshots += 1
            if snapshots_to_download is not None:
                console.log(f"Snapshot was collected - {downloaded_snapshots} of {snapshots_to_download}")
            else:
                console.log(f"Snapshot was collected")

            if not self._keep_local_snapshots:
                console.log(f"Remove:\n - {snapshot_path}\n - {archive_path}")

                shutil.rmtree(snapshot_path)
                os.remove(archive_path)

            self._last_upload = get_current_time()
