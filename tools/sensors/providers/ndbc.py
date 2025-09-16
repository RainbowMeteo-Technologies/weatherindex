import aiohttp
import asyncio
import io
import logging
import os
import re
import tarfile

from collections import Counter
from datetime import datetime
from sensors.utils.http import Http
from sensors.utils.iterable import batched
from sensors.providers.provider import BaseProvider
from typing_extensions import override


DAY_SECONDS = 24 * 60 * 60


class NdbcProvider(BaseProvider):

    def __init__(self, frequency: int = DAY_SECONDS, delay: int = DAY_SECONDS // 2, **kwargs):
        super().__init__("NDBC", frequency, delay, **kwargs)
        self._download_batch_size = int(os.getenv("NDBC_DOWNLOAD_BATCH_SIZE", 40))

    @override
    async def fetch_job(self, timestamp: int):
        """
        Fetch the data for the given timestamp

        Parameters
        ----------
        timestamp : int
            The timestamp of the data to fetch
        """
        downloaded_data = []

        async with aiohttp.ClientSession() as session:
            logging.info("Fetching sensor id list")
            raw = await Http.get_with_session("https://tao.ndbc.noaa.gov/tao/data_download/tao-esri.html", session)

            if raw is None:
                logging.error("Failed to fetch sensor id list")
                return

            logging.info("Parsing sensors id list")
            html = raw.decode("utf-8")
            sensor_pattern = r"\s{2,}addStation\(-?\d+,\s*-?\d+,\s*'\d+',\s*'(?P<id>[A-Z0-9]+)',\s*'(?P<group>TAO|TRITON)'\)"
            parsed_sensors = re.findall(sensor_pattern, html)
            if len(parsed_sensors) == 0:
                logging.error("No parseable sensor was found")
                return

            station_ids, station_groups = zip(*parsed_sensors)

            group_index = dict(Counter(station_groups))
            logging.info(f"Discovered {len(group_index)} sensor groups:")
            for k, v in group_index.items():
                logging.info(f"Group `{k}`: {v} sensors")

            logging.info("Requesting sensors observation data")
            day_ts = datetime.utcfromtimestamp(timestamp - self._frequency)

            base_url = ("https://tao.ndbc.noaa.gov/tao/data_download/process_results.php?type=rain&reso=hres"
                        f"&year1={day_ts.year}&mon1={day_ts.month:02d}&day1={day_ts.day:02d}"
                        f"&year2={day_ts.year}&mon2={day_ts.month:02d}&day2={day_ts.day:02d}"
                        "&format=subcdf&compression=gzip&stations=")

            batched_stations = batched(station_ids, self._download_batch_size)
            batched_urls = [f"{base_url}{'.'.join(stations)}" for stations in batched_stations]

            async def _fetch_archive(url: str) -> bytes | None:

                raw = await Http.get_with_session(url, session)
                if raw is None:
                    logging.error(f"Failed to query observation data from {url}")
                    return None

                logging.info(f"Discovering download link for observation data from {url}")
                html = raw.decode("utf-8")
                archive_pattern = r"<a href=\"(?P<link>cache/\d{6}/[a-zA-Z0-9\-]+\.tar\.gz)\">compressed file</a>"
                match = re.search(archive_pattern, html)
                if match is None:
                    logging.error(f"Failed to discover download link from {url}")
                    logging.info(html)
                    return None

                logging.info(f"Downloading observation data for {url}")
                url = os.path.join("https://tao.ndbc.noaa.gov/tao/data_download", match.group("link"))
                return await Http.get_with_session(url, session)

            downloaded_data = await asyncio.gather(*[_fetch_archive(url) for url in batched_urls],
                                                   return_exceptions=True)

        if len(downloaded_data) == 0:
            logging.error("Failed to download observations")
            return

        for data in downloaded_data:
            if isinstance(data, BaseException):
                logging.error(f"Encountered exception while downloading archive: {data}")
                continue

            if data is None:
                logging.warning("No data was downloaded from batch")
                continue

            logging.info(f"Downloaded {len(data)} bytes of observation data")

            logging.info("Saving observation data")
            file_like = io.BytesIO(data)
            with tarfile.open(fileobj=file_like, mode="r:gz") as tar:
                for member in tar.getmembers():
                    f = tar.extractfile(member)
                    if f is not None:
                        logging.info(f"Extracted {member.name}: {member.size} bytes")
                        await self._store_file(file_path=member.name,
                                               file_content=f.read())
