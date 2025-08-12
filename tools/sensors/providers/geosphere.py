import json
import logging
import datetime as dt
import aiohttp

from sensors.providers.provider import BaseProvider


class AustriaProvider(BaseProvider):
    """
    Provider for Austria Geosphere API-based observation service.

    This provider makes API calls to the Austria weather service and processes
    the GeoJSON responses to extract precipitation data for multiple stations.
    """

    # Hardcoded list of Austrian weather station IDs
    STATION_IDS = [
        "11034",   # WIEN-INNERE STADT
        "11238",   # GRAZ/STRASSGANG
        "11060",   # LINZ-STADT
        "11150",   # SALZBURG-FLUGHAFEN
        "11320",   # INNSBRUCK/UNIVERSITAET
        "8989076",  # KLAGENFURT/HTL1-LASTENSTRASSE
        "11149",   # OBERTAUERN
        "11311",   # ST.ANTON/ARLBERG
        "11144",   # ZELL AM SEE
    ]

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

        logging.info(f"Initialized GeoSphere provider with endpoint: {api_endpoint}")
        logging.info(f"Using {len(self.STATION_IDS)} hardcoded station IDs: {", ".join(self.STATION_IDS)}")

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
            # Construct the API URL with timestamp and station IDs
            url = self._construct_api_url(timestamp)

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

    def _construct_api_url(self, timestamp: int) -> str:
        """
        Construct the API URL for the given timestamp.

        Parameters
        ----------
        timestamp : int
            The timestamp to fetch data for

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
        station_ids_param = ",".join(self.STATION_IDS)

        # Construct URL with parameters
        url = (f"{self.api_endpoint}?"
               f"parameters=RR&"
               f"station_ids={station_ids_param}&"
               f"start={start_str}&"
               f"end={end_str}")

        logging.info(f"Constructed API URL: {url}")
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
            "User-Agent": "AustriaWeatherProvider/1.0",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        return headers

    async def _make_api_call(self, url: str, headers: dict):
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
        dict or None
            The API response data or None if failed
        """
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        logging.info(f"Successfully fetched data from GeoSphere API: {url}")
                        return data
                    else:
                        logging.error(f"GeoSphere API returned status {response.status}: {url}")
                        return None
        except aiohttp.ClientError as e:
            logging.error(f"HTTP client error calling GeoSphere API: {e}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error calling GeoSphere API: {e}")
            return None
