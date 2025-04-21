import aioboto3
import os
import logging

from sensors.publishers.publisher import Publisher
from sensors.utils.memory_zip import MemoryZip
from urllib.parse import urlparse


class S3Publisher(Publisher):
    def __init__(self, s3_uri: str):
        """
        Initialize the S3 publisher.

        Parameters
        ----------
        s3_uri : str
            The S3 URI to publish the data to. It will be concatenated with the file path on publish method call.
            For example: `s3://mybucket/folder` will be concatenated with `file_path.zip` to form the full S3 URI. As result,
            the data will be published to `s3://mybucket/folder/file_path.zip`.
        """
        self._s3_uri = s3_uri

    async def publish(self, publish_path: str, downloaded_file_path: str) -> None:
        """
        Publish the data to the S3 bucket.

        Parameters
        ----------
        publish_path : str
            The path of the file on the destination.
        downloaded_file_path : str
            The path to the file that was downloaded.
        """
        full_uri = os.path.join(self._s3_uri, publish_path)
        parsed_url = urlparse(full_uri)

        bucket_name = parsed_url.netloc
        object_key = parsed_url.path.lstrip("/")

        async with aioboto3.Session().client("s3") as s3:
            await s3.upload_file(downloaded_file_path, bucket_name, object_key)

        logging.info(f"Published {downloaded_file_path} to {full_uri}")
