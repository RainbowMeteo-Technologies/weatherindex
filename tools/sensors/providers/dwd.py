import aiohttp
import asyncio
import datetime as dt
import hashlib
import logging
import os
import re
import tempfile
import zipfile

from sensors.providers.provider import BaseProvider
from typing_extensions import override
from urllib.parse import urljoin


class DWDProvider(BaseProvider):
    """
    Provider for Germany DWD (Deutscher Wetterdienst) open data precipitation service.

    This provider downloads precipitation data from DWD's open data directory and processes
    the station-specific zip files to extract precipitation observations for multiple stations.

    See https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/10_minutes/precipitation/now/ for
    examples of how data is stored.
    """

    BASE_URL = "https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/10_minutes/precipitation/now/"
    META_FILE_URL = "https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/10_minutes/precipitation/now/zehn_now_rr_Beschreibung_Stationen.txt"
    DOWNLOAD_TIMEOUT = float(os.getenv("DWD_TIMEOUT", 30.0))

    def __init__(self, frequency: int = 600, delay: int = 5, **kwargs):
        """
        Initialize the provider.

        Parameters
        ----------
        frequency : int
            Frequency of data collection in seconds (default: 600 = 10 minutes)
        delay : int
            Additional delay in seconds
        """
        super().__init__("DWD", frequency, delay, **kwargs)
        self._timeout = self.DOWNLOAD_TIMEOUT
        self._last_meta_checksum = None

        logging.info(f"Initialized DWD provider with base URL: {self.BASE_URL}")

    @override
    async def fetch_job(self, timestamp: int):
        """
        Fetch the data for the given timestamp

        Parameters
        ----------
        timestamp : int
            The timestamp of the data to fetch

        Returns
        -------
        bool | None
            True if data was downloaded and stored, None if data was unchanged
        """
        try:
            logging.info("Checking if data has been updated by comparing meta-file checksum")
            current_checksum = await self._get_meta_file_checksum()

            if current_checksum is None:
                logging.error("Failed to fetch meta-file checksum, proceeding with download")
            elif current_checksum == self._last_meta_checksum:
                logging.info(f"Meta-file checksum unchanged ({current_checksum[:8]}...), data not updated")
                return
            else:
                logging.info(
                    f"Meta-file checksum changed from {self._last_meta_checksum[:8] if self._last_meta_checksum else 'None'}... to {current_checksum[:8]}..., proceeding with download")
                self._last_meta_checksum = current_checksum

            # Download all available station files
            logging.info("Fetching all available DWD station files")

            with tempfile.TemporaryDirectory() as temp_dir:
                # Download all station files
                downloaded_files = await self._download_station_files(temp_dir)

                if downloaded_files:
                    # Create a combined archive
                    archive_path = os.path.join(temp_dir, f"{timestamp}.zip")
                    await self._create_combined_archive(downloaded_files, archive_path)

                    # Store the combined archive
                    with open(archive_path, "rb") as f:
                        archive_content = f.read()

                    await self._store_file(f"{timestamp}.zip", archive_content)
                    logging.info(f"Successfully stored combined DWD data for timestamp {timestamp} from "
                                 f"{len(downloaded_files)} station files")
                else:
                    logging.error(f"Failed to download any DWD station files for timestamp {timestamp}")

        except BaseException as e:
            logging.error(f"Error fetching DWD data for timestamp {timestamp}: {e}")

    async def _get_meta_file_checksum(self) -> str | None:
        """
        Download the meta-file and calculate its checksum to detect changes.

        Returns
        -------
        str | None
            The SHA-256 checksum of the meta-file or None if failed
        """
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self._timeout)) as session:
                async with session.get(self.META_FILE_URL) as response:
                    if response.status == 200:
                        content = await response.read()
                        checksum = hashlib.sha256(content).hexdigest()
                        return checksum
                    else:
                        logging.error(f"Meta-file download returned status {response.status}")
                        return None
        except asyncio.TimeoutError as e:
            logging.error(f"Timeout error downloading meta-file (timeout: {self._timeout}s): {e}")
            return None
        except aiohttp.ClientError as e:
            logging.error(f"HTTP client error downloading meta-file: {e}")
            return None
        except BaseException as e:
            logging.error(f"Unexpected error downloading meta-file: {e}")
            return None

    async def _download_station_files(self, temp_dir: str) -> list[str]:
        """
        Download all available files from the DWD directory.

        Parameters
        ----------
        temp_dir : str
            Temporary directory for downloads

        Returns
        -------
        list[str]
            List of downloaded file paths
        """
        downloaded_files = []

        # Get list of available files from the directory
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self._timeout)) as session:
                content = None
                async with session.get(self.BASE_URL) as response:
                    if response.status == 200:
                        content = await response.text()
                    else:
                        logging.error(f"Failed to access DWD directory: status {response.status}")
                        return downloaded_files

                # Extract all files from the directory listing
                all_files = re.findall(r'href="([^"]*)"', content)
                # Filter out navigation links and keep only actual files
                files = [f for f in all_files if f and not f.startswith("?") and not f.startswith("/")]

                logging.info(f"Found {len(files)} files to download")

                # Create async download tasks for all files
                async def download_file(filename: str) -> str | None:
                    """Download a single file."""
                    try:
                        file_url = urljoin(self.BASE_URL, filename)
                        file_path = os.path.join(temp_dir, filename)

                        async with session.get(file_url) as file_response:
                            if file_response.status == 200:
                                content = await file_response.read()
                                with open(file_path, "wb") as f:
                                    f.write(content)

                                logging.info(f"Successfully downloaded {filename}")
                                return file_path
                            else:
                                logging.warning(f"Failed to download {filename}: status {file_response.status}")
                                return None

                    except asyncio.TimeoutError as e:
                        logging.error(f"Timeout error downloading {filename} (timeout: {self._timeout}s): {e}")
                        return None
                    except aiohttp.ClientError as e:
                        logging.error(f"HTTP client error downloading {filename}: {e}")
                        return None
                    except BaseException as e:
                        logging.error(f"Unexpected error downloading {filename}: {e}")
                        return None

                # Download all files concurrently
                tasks = [download_file(filename) for filename in files]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Collect successful downloads
                for result in results:
                    if isinstance(result, BaseException):
                        logging.error(f"File download failed with exception: {result}")
                    elif result is not None:
                        downloaded_files.append(result)

        except asyncio.TimeoutError as e:
            logging.error(f"Timeout error accessing DWD directory (timeout: {self._timeout}s): {e}")
        except aiohttp.ClientError as e:
            logging.error(f"HTTP client error accessing DWD directory: {e}")
        except BaseException as e:
            logging.error(f"Unexpected error accessing DWD directory: {e}")

        return downloaded_files

    async def _create_combined_archive(self, file_paths: list[str], archive_path: str):
        """
        Create a combined ZIP archive from multiple station files.

        Parameters
        ----------
        file_paths : list[str]
            List of file paths to include in the archive
        archive_path : str
            Path for the output archive
        """
        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for file_path in file_paths:
                if os.path.exists(file_path):
                    # Add file to archive with relative path
                    archive.write(file_path, os.path.basename(file_path))

    def _get_headers(self) -> dict:
        """
        Get the headers for the HTTP request.

        Returns
        -------
        dict
            Headers dictionary
        """
        headers = {
            "User-Agent": "DWDWeatherProvider/1.0",
            "Accept": "*/*"
        }

        return headers
