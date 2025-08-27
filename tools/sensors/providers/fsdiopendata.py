import aiohttp
import asyncio
import datetime as dt
import json
import logging
import os
import tempfile
import zipfile

from sensors.providers.provider import BaseProvider
from typing_extensions import override


class FSDIOpenDataProvider(BaseProvider):
    """
    Provider for Switzerland FSDI Open Data STAC API precipitation service.

    This provider downloads precipitation data from the Swiss STAC API and processes
    the CSV responses to extract precipitation observations for multiple stations.

    Documentation: https://opendatadocs.meteoschweiz.ch/general/download#how-to-download-files-automatically
    """

    API_ENDPOINT = "https://data.geo.admin.ch/api/stac/v1/collections/ch.meteoschweiz.ogd-smn-precip/items"
    DOWNLOAD_TIMEOUT = float(os.getenv("FSDIOPENDATA_TIMEOUT", 30.0))

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
        super().__init__("FSDIOpenData", frequency, delay, **kwargs)
        self._timeout = self.DOWNLOAD_TIMEOUT

        logging.info(f"Initialized FSDIOpenData provider with endpoint: {self.API_ENDPOINT}")

    @override
    async def fetch_job(self, timestamp: int):
        """
        Fetch the data for the given timestamp

        Parameters
        ----------
        timestamp : int
            The timestamp of the data to fetch
        """
        try:
            # Download STAC API response and all CSV files
            logging.info("Fetching STAC API response and CSV files")

            # Create a temporary directory for downloads
            with tempfile.TemporaryDirectory() as temp_dir:
                # Download STAC API response
                stac_data = await self._fetch_stac_data()

                if not stac_data:
                    logging.error("Failed to fetch STAC API data")
                    return

                # Store the STAC API response
                stac_file_path = os.path.join(temp_dir, "stac_response.json")
                with open(stac_file_path, "w", encoding="utf-8") as f:
                    json.dump(stac_data, f, ensure_ascii=False, indent=2)

                # Download all CSV files
                downloaded_files = await self._download_csv_files(stac_data, temp_dir)

                if downloaded_files:
                    # Create a combined archive
                    archive_path = os.path.join(temp_dir, f"{timestamp}.zip")
                    await self._create_combined_archive([stac_file_path] + downloaded_files, archive_path)

                    # Store the combined archive
                    with open(archive_path, "rb") as f:
                        archive_content = f.read()

                    await self._store_file(f"{timestamp}.zip", archive_content)
                    logging.info(f"Successfully stored combined FSDIOpenData for timestamp {timestamp} from "
                                 f"{len(downloaded_files)} CSV files")
                else:
                    logging.error(f"Failed to download any CSV files for timestamp {timestamp}")

        except BaseException as e:
            logging.error(f"Error fetching FSDIOpenData for timestamp {timestamp}: {e}")

    async def _fetch_stac_data(self) -> dict | None:
        """
        Fetch the STAC API response.

        Returns
        -------
        dict | None
            The STAC API response data or None if failed
        """
        try:
            headers = self._get_headers()

            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self._timeout)) as session:
                async with session.get(self.API_ENDPOINT, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        logging.info(
                            f"Successfully fetched STAC API data with {len(data.get('features', []))} stations")
                        return data
                    else:
                        logging.error(f"STAC API returned status {response.status}")
                        return None
        except asyncio.TimeoutError as e:
            logging.error(f"Timeout error calling STAC API (timeout: {self._timeout}s): {e}")
            return None
        except aiohttp.ClientError as e:
            logging.error(f"HTTP client error calling STAC API: {e}")
            return None
        except BaseException as e:
            logging.error(f"Unexpected error calling STAC API: {e}")
            return None

    async def _download_csv_files(self, stac_data: dict, temp_dir: str) -> list[str]:
        """
        Download all CSV files from the STAC API response.

        Parameters
        ----------
        stac_data : dict
            The STAC API response data
        temp_dir : str
            Temporary directory for downloads

        Returns
        -------
        list[str]
            List of downloaded file paths
        """
        downloaded_files = []

        try:
            features = stac_data.get("features", [])
            logging.info(f"Found {len(features)} stations in STAC response")

            # Create async download tasks for all CSV files
            async def download_csv_file(feature: dict) -> str | None:
                """Download a single CSV file for a station."""
                try:
                    station_id = feature.get("id")
                    if not station_id:
                        logging.warning(f"Station feature missing ID: {feature}")
                        return None

                    # Find the "_t_now.csv" asset
                    assets = feature.get("assets", {})
                    csv_asset = None
                    for asset_name, asset_data in assets.items():
                        if asset_name.endswith("_t_now.csv"):
                            csv_asset = asset_data
                            break

                    if not csv_asset:
                        logging.warning(f"No '_t_now.csv' asset found for station {station_id}")
                        return None

                    # Download the CSV file
                    csv_url = csv_asset.get("href")
                    if not csv_url:
                        logging.warning(f"No href found for CSV asset in station {station_id}")
                        return None

                    file_path = os.path.join(temp_dir, f"{station_id}_t_now.csv")

                    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self._timeout)) as session:
                        async with session.get(csv_url, headers=self._get_headers()) as response:
                            if response.status == 200:
                                content = await response.read()
                                with open(file_path, "wb") as f:
                                    f.write(content)

                                logging.info(f"Successfully downloaded CSV for station {station_id}")
                                return file_path
                            else:
                                logging.warning(
                                    f"Failed to download CSV for station {station_id}: status {response.status}")
                                return None

                except asyncio.TimeoutError as e:
                    logging.error(
                        f"Timeout error downloading CSV for station {feature.get('id', 'unknown')} (timeout: {self._timeout}s): {e}")
                    return None
                except aiohttp.ClientError as e:
                    logging.error(f"HTTP client error downloading CSV for station {feature.get('id', 'unknown')}: {e}")
                    return None
                except BaseException as e:
                    logging.error(f"Unexpected error downloading CSV for station {feature.get('id', 'unknown')}: {e}")
                    return None

            # Download all CSV files concurrently
            tasks = [download_csv_file(feature) for feature in features]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Collect successful downloads
            for result in results:
                if isinstance(result, BaseException):
                    logging.error(f"CSV download failed with exception: {result}")
                elif result is not None:
                    downloaded_files.append(result)

            logging.info(f"Successfully downloaded {len(downloaded_files)} CSV files out of {len(features)} stations")

        except BaseException as e:
            logging.error(f"Error downloading CSV files: {e}")

        return downloaded_files

    async def _create_combined_archive(self, file_paths: list[str], archive_path: str):
        """
        Create a combined ZIP archive from multiple files.

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
        headers = {"User-Agent": "FSDIOpenDataWeatherProvider/1.0",
                   "Accept": "application/json,text/csv,*/*"}

        return headers
