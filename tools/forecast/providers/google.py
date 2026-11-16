import asyncio
import json
import os

from forecast.providers.provider import BaseRateLimitedForecastInPointProvider
from forecast.utils.req_interface import RequestInterface, Response
from rich.console import Console
from typing_extensions import override  # for python <3.12

console = Console()


class Google(BaseRateLimitedForecastInPointProvider, RequestInterface):
    """Google Maps Platform Weather API minute forecast
    https://developers.google.com/maps/documentation/weather/minute-forecast
    """

    GOOGLE_API_BASE_URL = os.getenv("GOOGLE_API_BASE_URL", "https://weather.googleapis.com")
    MINUTE_FORECAST_ENDPOINT = "v1/forecast/minutes:lookup"
    DEFAULT_PAGE_SIZE = 30

    def __init__(self, token: str, page_size: int = DEFAULT_PAGE_SIZE, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token = token
        self.page_size = page_size

    async def rate_limit_aware_get(self, url: str, params: dict[str, str]) -> Response:
        resp = Response()

        while not resp.ok:
            resp = await self._native_get(url=url, params=params)

            if resp.status != 429:  # Status code for too many requests
                return resp

            time_to_sleep = None

            if resp.headers:
                for key, value in resp.headers.items():
                    if key.lower() == "retry-after":
                        time_to_sleep = float(value)

            if time_to_sleep is not None:
                console.log(f"Rate limit exceeded. Waiting for {time_to_sleep} seconds.")
                await asyncio.sleep(time_to_sleep)
            else:
                break

        return resp

    def _get_url(self) -> str:
        return f"{self.GOOGLE_API_BASE_URL.rstrip('/')}/{self.MINUTE_FORECAST_ENDPOINT}"

    def _get_params(self, lon: float, lat: float) -> dict[str, str]:
        # Exactly one request per sensor: nextPageToken is ignored
        return {
            "key": self.token,
            "location.latitude": str(lat),
            "location.longitude": str(lon),
            "unitsSystem": "METRIC",
            "pageSize": str(self.page_size),
        }

    @override
    async def get_json_forecast_in_point(self, lon: float, lat: float) -> Response:
        resp = await self.rate_limit_aware_get(url=self._get_url(), params=self._get_params(lon=lon, lat=lat))
        if resp.ok:
            resp.payload = json.dumps({
                "position": {
                    "lon": lon,
                    "lat": lat
                },
                "payload": json.loads(resp.payload)
            })
        return resp
