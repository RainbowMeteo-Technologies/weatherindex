import asyncio
import logging
import os
import time

from sensors.publishers.publisher import Publisher
from sensors.utils.memory_zip import MemoryZip
from sensors.utils.time import time_to_next_run, Timestamp


class BaseProvider:

    def __init__(self,
                 service: str,
                 frequency: int,
                 delay: int,
                 publisher: Publisher,
                 download_path: str):
        """
        Initialize the provider.

        Parameters
        ----------
        service : str
            The service name.
        frequency : int
            The frequency of the provider in seconds.
        delay : int
            Additional delay in seconds. It used to wait for the data to be available.
        publisher : Publisher
            The publisher to publish the data. Local storage or any cloud storage.
        download_path : str
            The path to store the downloaded data.
        """
        self._service = service
        self._frequency = frequency
        self._delay = delay
        self._publisher = publisher
        self._download_path = download_path

        logging.info(f"Create provider {self._service} with frequency={self._frequency}, delay={self._delay}")

        self._storage: MemoryZip = None

    async def run(self):
        """
        Run the provider.
        """
        while True:
            time_to_sleep = time_to_next_run(self._frequency) + self._delay
            logging.info(f"Next data for {self._service} will be available in {time_to_sleep} seconds.")
            await asyncio.sleep(time_to_sleep)

            start_time = time.time()

            # Create a new storage for each run
            self._storage = MemoryZip()

            timestamp = Timestamp.floor(Timestamp.get_current(), self._frequency)

            await self.fetch_job(timestamp)

            # Close the storage
            self._storage.close()

            # Save the storage to the download path
            os.makedirs(self._download_path, exist_ok=True)
            file_name = f"{timestamp}.zip"
            file_path = os.path.join(self._download_path, file_name)
            with open(file_path, "wb") as file:
                file.write(self._storage.buffer.getvalue())

            # Publish to the storage
            await self._publisher.publish(publish_path=file_name,
                                          downloaded_file_path=file_path)

            # Remove the file
            try:
                logging.info(f"Removing file {file_path}")
                os.remove(file_path)
            except Exception as e:
                logging.error(f"Error removing file {file_path}: {e}")

            logging.info(f"It took {time.time() - start_time} seconds to download data for {self._service}")

    async def fetch_job(self, timestamp: int):
        """
        Fetch the data for the given timestamp

        Parameters
        ----------
        timestamp : int
            The timestamp of the data to fetch
        """
        raise NotImplementedError("fetch_job must be implemented by the provider")

    async def _store_file(self, file_path: str, file_content: str):
        """
        Store the file in the storage.

        Parameters
        ----------
        file_path : str
            The path to the file.
        file_content : str
            The content of the file.
        """
        self._storage.write_raw(file_path=file_path,
                                data=file_content)
