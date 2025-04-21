import gzip
import logging
import datetime as dt

from sensors.providers.provider import BaseProvider
from sensors.utils.http import Http


class MetarSource(BaseProvider):

    def __init__(self, frequency: int = 120, delay: int = 5, **kwargs):
        super().__init__("METAR", frequency, delay, **kwargs)

    async def fetch_job(self, timestamp: int):
        """
        Fetch the data for the given timestamp

        Parameters
        ----------
        timestamp : int
            The timestamp of the data to fetch
        """
        logging.info(f"Running a task {self._service} {timestamp} / {dt.datetime.fromtimestamp(timestamp).isoformat()}")

        await self.fetch_data(timestamp)

        logging.info(f"Completing a {self._service} task")

    async def fetch_data(self, timestamp: int):
        """
        Fetch the data for the given timestamp

        Parameters
        ----------
        timestamp : int
            The timestamp of the data to fetch
        """
        try:
            data = await Http.get("https://aviationweather.gov/data/cache/metars.cache.xml.gz")
            # we need to decompress the data and put raw xml data into the storage
            data = gzip.decompress(data)
            # put the data into the storage
            await self._store_file(f"{timestamp}.xml", data)

        except Exception as e:
            logging.error(e)
