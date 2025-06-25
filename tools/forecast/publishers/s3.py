import aioboto3
import os

from urllib.parse import urlparse
from forecast.publishers.publisher import Publisher

from rich.console import Console

console = Console()


class S3Publisher(Publisher):
    def __init__(self, s3_uri: str):
        self._s3_uri = s3_uri

    async def publish(self, snapshot_path: str) -> None:
        console.log(f"Publishing {snapshot_path} to {self._s3_uri}")

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
