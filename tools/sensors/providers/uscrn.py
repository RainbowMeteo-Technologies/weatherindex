import asyncio
import logging
import re

from datetime import datetime, timezone
from sensors.providers.provider import BaseProvider
from sensors.utils.http import Http
from sensors.utils.memory_zip import MemoryZip
from sensors.utils.time import Timestamp
from typing_extensions import override

BASE_URL = "https://www.ncei.noaa.gov/pub/data/uscrn/products/subhourly01"

# Each run keeps the last 3 h of 5-minute rows of every sensor file
TAIL_SECONDS = 3 * 3600
TAIL_ROWS = TAIL_SECONDS // 300
# Size of one CRNS0101-05 fixed-width row in bytes: 135 columns plus the newline
ROW_BYTES = 136
# One extra row is requested because the first (partial) line of the tail is cut away
TAIL_BYTES = (TAIL_ROWS + 1) * ROW_BYTES
# The tail window is 3 h. Yearly files may be split by local standard time (down to UTC-10 for HI),
# so the previous year is also read until 3 h + 12 h after the UTC new year.
YEAR_LOOKBACK = TAIL_SECONDS + 12 * 3600

_FILE_NAME_RE = re.compile(r'href="(CRNS0101-05-\d{4}-[^"/]+\.txt)"')


class UscrnSource(BaseProvider):
    """
    USCRN subhourly (5-minute) observations from NCEI.

    Every run stores one snapshot with the raw tail of every sensor file of the current year
    (and of the previous year right after the new year).
    """

    def __init__(self, frequency: int = 3600, delay: int = 300, concurrency: int = 8, **kwargs):
        super().__init__("USCRN", frequency, delay, **kwargs)
        self._concurrency = concurrency

    @override
    async def fetch_job(self, timestamp: int):
        """
        Store the tail of every sensor file that can hold rows of the last 3 h before `timestamp`.

        Parameters
        ----------
        timestamp : int
            The snapshot timestamp
        """
        file_urls = []
        for year in _years_between(timestamp - YEAR_LOOKBACK, timestamp):
            file_urls += [(name, f"{BASE_URL}/{year}/{name}") for name in await _list_files(year)]

        semaphore = asyncio.Semaphore(self._concurrency)

        async def fetch_tail(file_name: str, url: str):
            try:
                async with semaphore:
                    data = await Http.get(url, headers={"Range": f"bytes=-{TAIL_BYTES}"})
                if data is None:
                    logging.error(f"Wasn't able to download the tail of {file_name}")
                    return
                await self._store_file(file_name, cut_to_complete_lines(data, TAIL_BYTES))
            except Exception as ex:
                logging.error(f"Wasn't able to download the tail of {file_name}: {ex}")

        await asyncio.gather(*[fetch_tail(name, url) for name, url in file_urls])

    async def backfill(self, start: int, end: int):
        """
        Rebuild the hourly snapshots for `[start, end]` from the NCEI yearly files.

        Every snapshot `<ts>.zip` has the downloader layout: one entry per sensor file with its rows
        whose UTC time is in `(ts - 3h, ts]`.

        Parameters
        ----------
        start : int
            The first snapshot timestamp (rounded up to the hour)
        end : int
            The last snapshot timestamp (rounded down to the hour)
        """
        first = Timestamp.floor(start + self._frequency - 1, self._frequency)
        last = Timestamp.floor(end, self._frequency)
        timestamps = range(first, last + 1, self._frequency)
        if len(timestamps) == 0:
            logging.warning(f"No snapshots to backfill between {start} and {end}")
            return

        # snapshot timestamp -> sensor file name -> rows
        snapshots: dict[int, dict[str, list[bytes]]] = {ts: {} for ts in timestamps}

        file_urls = []
        for year in _years_between(first - YEAR_LOOKBACK, last):
            file_urls += [(name, f"{BASE_URL}/{year}/{name}") for name in await _list_files(year)]

        semaphore = asyncio.Semaphore(self._concurrency)

        async def fetch_file(file_name: str, url: str):
            try:
                async with semaphore:
                    data = await Http.get(url)
                if data is None:
                    logging.error(f"Wasn't able to download {file_name}")
                    return
                for line in data.splitlines(keepends=True):
                    if not line.endswith(b"\n"):
                        continue
                    valid_time = _row_utc_timestamp(line)
                    # the row belongs to the 3 snapshots whose (ts - 3h, ts] window holds it
                    snapshot_time = Timestamp.floor(valid_time + self._frequency - 1, self._frequency)
                    while snapshot_time - TAIL_SECONDS < valid_time:
                        if snapshot_time in snapshots:
                            snapshots[snapshot_time].setdefault(file_name, []).append(line)
                        snapshot_time += self._frequency
            except Exception as ex:
                logging.error(f"Wasn't able to backfill {file_name}: {ex}")

        await asyncio.gather(*[fetch_file(name, url) for name, url in file_urls])

        for timestamp, files in snapshots.items():
            if not files:
                logging.info(f"No USCRN rows for snapshot {timestamp}, skipping")
                continue
            self._storage = MemoryZip()
            for file_name in sorted(files):
                await self._store_file(file_name, b"".join(files[file_name]))
            self._storage.close()
            await self._publish_storage(timestamp)


def _row_utc_timestamp(line: bytes) -> int:
    """UTC timestamp of a CRNS0101-05 row from its UTC_DATE (columns 7-14) and UTC_TIME (columns 16-19)."""
    return int(datetime.strptime(line[6:19].decode("ascii"), "%Y%m%d %H%M").replace(tzinfo=timezone.utc).timestamp())


def _years_between(begin: int, end: int) -> range:
    return range(datetime.fromtimestamp(begin, tz=timezone.utc).year,
                 datetime.fromtimestamp(end, tz=timezone.utc).year + 1)


async def _list_files(year: int) -> list[str]:
    """
    Sensor file names in the NCEI directory of the year. Empty when the directory is unavailable,
    for example a new year directory that NCEI hasn't created yet.
    """
    try:
        listing = await Http.get(f"{BASE_URL}/{year}/")
    except Exception as ex:
        logging.error(f"Wasn't able to list USCRN files of {year}: {ex}")
        return []
    if listing is None:
        logging.error(f"Wasn't able to list USCRN files of {year}")
        return []
    return sorted(set(_FILE_NAME_RE.findall(listing.decode("utf-8", errors="replace"))))


def cut_to_complete_lines(data: bytes, tail_bytes: int) -> bytes:
    """
    Keep only complete lines of a file tail.

    Parameters
    ----------
    data : bytes
        The answer to a `bytes=-<tail_bytes>` range request. A server that ignores `Range` returns the whole file.
    tail_bytes : int
        The number of requested bytes.

    Returns
    -------
    bytes
        The tail without the partial first line (when the tail starts inside the file)
        and without the partial last line (when the file is being appended).
    """
    if len(data) >= tail_bytes:
        # the tail starts inside the file, so its first line is partial
        data = data[-tail_bytes:]
        data = data[data.find(b"\n") + 1:] if b"\n" in data else b""
    return data[:data.rfind(b"\n") + 1]
