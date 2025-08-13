import json
import logging
import datetime as dt
import aiohttp

from sensors.providers.provider import BaseProvider


class GeoSphereProvider(BaseProvider):
    """
    Provider for Austria Geosphere API-based observation service.

    This provider makes API calls to the Austria weather service and processes
    the GeoJSON responses to extract precipitation data for multiple stations.
    """

    def __init__(self, frequency: int = 600, delay: int = 5,
                 api_endpoint: str = "https://dataset.api.hub.geosphere.at/v1/station/historical/tawes-v1-10min",
                 timeout: int = 30, **kwargs):
        """
        Initialize the provider.

        Parameters
        ----------
        frequency : int
            Frequency of data collection in seconds (default: 600 = 10 minutes)
        delay : int
            Additional delay in seconds
        api_endpoint : str
            Base URL for the Austria Geosphere API
        timeout : int
            Request timeout in seconds
        """
        super().__init__("GeoSphere", frequency, delay, **kwargs)
        self.api_endpoint = api_endpoint
        self.timeout = timeout
        self._station_ids: list[str] | None = None

        logging.info(f"Initialized GeoSphere provider with endpoint: {api_endpoint}")

    async def _fetch_station_ids(self) -> list[str]:
        """
        Fetch the list of active station IDs from the metadata API.

        Returns
        -------
        list[str]
            List of active station IDs
        """
        if self._station_ids is not None:
            return self._station_ids

        try:
            # Use the same endpoint but with /metadata suffix
            metadata_url = f"{self.api_endpoint}/metadata"
            headers = self._get_headers()

            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
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

                            # Cache the station IDs
                            self._station_ids = station_ids
                            return station_ids
                        else:
                            logging.error("No 'stations' key found in metadata response")
                            return []
                    else:
                        logging.error(f"Metadata API returned status {response.status}")
                        return []

        except Exception as e:
            logging.error(f"Error fetching station IDs from metadata API: {e}")
            return []

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
            # Get the list of active station IDs
            station_ids = await self._fetch_station_ids()

            if not station_ids:
                logging.error("No active station IDs available, cannot fetch data")
                return

            logging.info(f"Fetching data for {len(station_ids)} active stations")

            # Construct the API URL with timestamp and station IDs
            url = self._construct_api_url(timestamp, station_ids)

            # Make the API call
            headers = self._get_headers()
            data = await self._make_api_call(url, headers)

            if data:
                # Store the raw API response directly without processing
                await self._store_file(f"{timestamp}.json", json.dumps(data).encode("utf-8"))
                logging.info(f"Successfully stored raw GeoSphere API data for timestamp {timestamp}")
            else:
                logging.error(f"Failed to fetch data from GeoSphere API for timestamp {timestamp}")

        except Exception as e:
            logging.error(f"Error fetching GeoSphere data for timestamp {timestamp}: {e}")

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
        # Convert timestamp to datetime for API parameters
        dt_obj = dt.datetime.fromtimestamp(timestamp)

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
        url = (f"{self.api_endpoint}?"
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
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        logging.info(f"Successfully fetched data from GeoSphere API")
                        return data
                    else:
                        logging.error(f"GeoSphere API returned status {response.status}")
                        return None
        except aiohttp.ClientError as e:
            logging.error(f"HTTP client error calling GeoSphere API: {e}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error calling GeoSphere API: {e}")
            return None
