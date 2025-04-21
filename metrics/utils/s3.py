import boto3
import botocore
import os
import typing

from urllib.parse import urlparse


class S3Client:

    def __init__(self):
        self._client = boto3.client('s3')

    def download_file(self,
                      s3_uri: str,
                      file_path: str,
                      callback: typing.Callable[[int, int], None] = None,
                      force: bool = False) -> bool:
        """Downloads file from s3 to specified path. Authorization data for S3 should be placed into env variables.
        Function checks if file exists and do not download it if it has the same size. You can force download anyway by using flag `force`
        Parameters
        ----------
        s3_uri : str
            S3 URI of the object top download
        file_path : str
            File path where to save downloaded file
        callback : typing.Callable[[int, int], None]
            Callback function to track download progress. This function should receive two arguments: `bytes_transferred`, `total_bytes`.
            By default it is None
        force : bool
            If this flag is `True`, then file will be download anyway.

        Returns
        -------
        bool
            Returns `True` when file downloaded or already exists; otherwise returns `False`
        """
        parsed_uri = urlparse(s3_uri)

        # extract the bucket name and object key
        bucket_name = parsed_uri.netloc
        object_key = parsed_uri.path.lstrip('/')

        try:
            total_bytes = self._client.head_object(Bucket=bucket_name, Key=object_key)['ContentLength']
            if not force and os.path.exists(file_path):
                file_stats = os.stat(file_path)
                if file_stats.st_size == total_bytes:
                    return True

            if callback:
                def _callback_wrap(bytes_transferred: int):
                    callback(bytes_transferred, total_bytes)

                self._client.download_file(bucket_name, object_key, file_path,
                                           Callback=_callback_wrap)
            else:
                self._client.download_file(bucket_name, object_key, file_path)
        except botocore.exceptions.ClientError as ex:
            # logging/alert
            return False

        return True
