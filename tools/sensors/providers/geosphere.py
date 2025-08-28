import aiohttp
import asyncio
import datetime as dt
import json
import logging
import os

from sensors.providers.provider import BaseProvider
from typing_extensions import override


class GeoSphereProvider(BaseProvider):
    """
    Provider for Austria Geosphere API-based observation service.

    This provider makes API calls to the Austria weather service and processes
    the GeoJSON responses to extract precipitation data for multiple stations.

    Documentation: https://dataset.api.hub.geosphere.at/v1/docs/
    """

    API_ENDPOINT = "https://dataset.api.hub.geosphere.at/v1/station/historical/tawes-v1-10min"
    DOWNLOAD_TIMEOUT = float(os.getenv("GEOSPHERE_TIMEOUT", 30.0))

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
        super().__init__("GeoSphere", frequency, delay, **kwargs)
        self._timeout = self.DOWNLOAD_TIMEOUT

        logging.info(f"Initialized GeoSphere provider with endpoint: {self.API_ENDPOINT}")

    async def _fetch_station_ids(self) -> list[str]:
        """
        Fetch the list of active station IDs from the metadata API.

        Returns
        -------
        list[str]
            List of active station IDs
        """
        try:
            # Use the same endpoint but with /metadata suffix
            metadata_url = f"{self.API_ENDPOINT}/metadata"
            headers = self._get_headers()

            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self._timeout)) as session:
                async with session.get(metadata_url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()

                        if "stations" in data:
                            stations = data["stations"]
                            # Filter for active stations only
                            active_stations = [station for station in stations if station.get("is_active", False)]

                            # Extract station IDs
                            station_ids = [station["id"] for station in active_stations]

                            logging.info(f"Successfully fetched {len(station_ids)} active stations from metadata API")
                            logging.info(f"Total stations in metadata: {len(stations)}")

                            return station_ids
                        else:
                            logging.error("No 'stations' key found in metadata response")
                            return []
                    else:
                        logging.error(f"Metadata API returned status {response.status}")
                        return []

        except BaseException as e:
            logging.error(f"Error fetching station IDs from metadata API: {e}")
            return []

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
            # Get the list of active station IDs
            station_ids = await self._fetch_station_ids()

            if not station_ids:
                logging.error("No active station IDs available, cannot fetch data")
                return

            logging.info(f"Fetching data for {len(station_ids)} active stations")

            # Split station IDs into chunks of 100 to avoid URL length limits
            chunk_size = 100
            station_id_chunks = [station_ids[i:i + chunk_size] for i in range(0, len(station_ids), chunk_size)]

            logging.info(f"Split {len(station_ids)} stations into {len(station_id_chunks)} chunks of max {chunk_size}")

            # Create a list of async jobs for concurrent execution
            async def fetch_chunk(chunk_index: int, chunk: list[str]) -> tuple[int, dict | None]:
                """Fetch data for a single chunk of stations."""
                logging.info(f"Processing chunk {chunk_index + 1}/{len(station_id_chunks)} with {len(chunk)} stations")

                # Construct the API URL with this chunk of station IDs
                url = self._construct_api_url(timestamp, chunk)

                # Make the API call for this chunk
                headers = self._get_headers()
                chunk_data = await self._make_api_call(url, headers)

                if chunk_data:
                    logging.info(f"Successfully fetched data for chunk {chunk_index + 1} with {len(chunk)} stations")
                else:
                    logging.error(f"Failed to fetch data for chunk {chunk_index + 1} with {len(chunk)} stations")

                return chunk_index, chunk_data

            # Create all the async jobs
            jobs = [fetch_chunk(i, chunk) for i, chunk in enumerate(station_id_chunks)]

            # Execute all jobs concurrently
            logging.info(f"Executing {len(jobs)} chunk requests concurrently")
            results = await asyncio.gather(*jobs, return_exceptions=True)

            # Process results and collect successful data
            all_data = []
            for chunk_index, result in results:
                if isinstance(result, BaseException):
                    logging.error(f"Chunk {chunk_index + 1} failed with exception: {result}")
                elif result is not None:
                    all_data.append(result)
                    logging.info(f"Collected data from chunk {chunk_index + 1}")
                else:
                    logging.warning(f"Chunk {chunk_index + 1} returned no data")

            if all_data:
                # Combine all chunk data into a single response
                combined_data = self._combine_chunk_data(all_data)

                # Store the combined data
                await self._store_file(f"{timestamp}.json", json.dumps(combined_data).encode("utf-8"))
                logging.info(f"Successfully stored combined GeoSphere API data for timestamp {timestamp} from "
                             f"{len(station_id_chunks)} chunks")
            else:
                logging.error(f"Failed to fetch data from any GeoSphere API chunks for timestamp {timestamp}")

        except BaseException as e:
            logging.error(f"Error fetching GeoSphere data for timestamp {timestamp}: {e}")

    def _combine_chunk_data(self, chunk_data_list: list[dict]) -> dict:
        """
        Combine data from multiple API calls into a single response.

        Parameters
        ----------
        chunk_data_list : list[dict]
            List of API response data from different chunks

        Returns
        -------
        dict
            Combined data with merged timestamps and features
        """
        if not chunk_data_list:
            return {}

        if len(chunk_data_list) == 1:
            return chunk_data_list[0]

        # Initialize combined data structure
        combined_data = {"timestamps": [],
                         "features": []}

        # Collect all unique timestamps
        all_timestamps = set()
        for chunk_data in chunk_data_list:
            if "timestamps" in chunk_data:
                all_timestamps.update(chunk_data["timestamps"])

        # Sort timestamps chronologically
        combined_data["timestamps"] = sorted(list(all_timestamps))

        # Collect all features from all chunks
        for chunk_data in chunk_data_list:
            if "features" in chunk_data:
                combined_data["features"].extend(chunk_data["features"])

        logging.info(f"Combined {len(chunk_data_list)} chunks into single response with "
                     f"{len(combined_data['timestamps'])} timestamps and {len(combined_data['features'])} features")

        return combined_data

    def _construct_api_url(self, timestamp: int, station_ids: list[str]) -> str:
        """
        Construct the API URL for the given timestamp and station IDs.

        Parameters
        ----------
        timestamp : int
            The timestamp to fetch data for
        station_ids : list[str]
            List of station IDs to fetch data for

        Returns
        -------
        str
            The complete API URL
        """
        # Convert timestamp to UTC datetime for API parameters
        # Use utcfromtimestamp to ensure consistent UTC time regardless of system timezone
        dt_obj = dt.datetime.utcfromtimestamp(timestamp)

        # Calculate time range: 6 hours centered around the timestamp
        # This matches the example API call (10:00 to 16:00)
        start_time = dt_obj - dt.timedelta(hours=3)
        end_time = dt_obj + dt.timedelta(hours=3)

        # Format times for API (YYYY-MM-DDTHH:MM)
        start_str = start_time.strftime("%Y-%m-%dT%H:%M")
        end_str = end_time.strftime("%Y-%m-%dT%H:%M")

        # Join station IDs with commas
        station_ids_param = ",".join(station_ids)

        # Construct URL with parameters
        url = (f"{self.API_ENDPOINT}?"
               f"parameters=RR&"
               f"station_ids={station_ids_param}&"
               f"start={start_str}&"
               f"end={end_str}")

        logging.info(f"Constructed API URL for {len(station_ids)} stations")
        return url

    def _get_headers(self) -> dict:
        """
        Get the headers for the API request.

        Returns
        -------
        dict
            Headers dictionary
        """
        headers = {
            "User-Agent": "GeoSphereWeatherProvider/1.0",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        return headers

    async def _make_api_call(self, url: str, headers: dict) -> dict | None:
        """
        Make the actual API call.

        Parameters
        ----------
        url : str
            The API URL to call
        headers : dict
            Headers for the request

        Returns
        -------
        dict | None
            The API response data or None if failed
        """
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self._timeout)) as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        logging.info(f"Successfully fetched data from GeoSphere API")
                        return data
                    else:
                        logging.error(f"GeoSphere API returned status {response.status}")
                        return None
        except asyncio.TimeoutError as e:
            logging.error(f"Timeout error calling GeoSphere API (timeout: {self._timeout}s): {e}")
            return None
        except aiohttp.ClientError as e:
            logging.error(f"HTTP client error calling GeoSphere API: {e}")
            return None
        except BaseException as e:
            logging.error(f"Unexpected error calling GeoSphere API: {e}")
            return None
