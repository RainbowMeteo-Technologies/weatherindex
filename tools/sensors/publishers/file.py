import os
import logging
import shutil

from sensors.publishers.publisher import Publisher
from sensors.utils.memory_zip import MemoryZip


class FilePublisher(Publisher):
    def __init__(self, output_directory: str):
        """
        Initialize the file publisher.

        Parameters
        ----------
        output_directory : str
            The path to the directory to store the files.
        """
        self._output_directory = output_directory

    async def publish(self, publish_path: str, downloaded_file_path: str) -> None:
        """
        Publish the data to the file.

        Parameters
        ----------
        file_path : str
            The path to the file to be published.
        storage : MemoryZip
            The storage to be published.
        """
        os.makedirs(self._output_directory, exist_ok=True)
        # copy the file to the output directory
        shutil.copy(downloaded_file_path, os.path.join(self._output_directory, publish_path))

        logging.info(f"Published {downloaded_file_path} to {self._output_directory}")
