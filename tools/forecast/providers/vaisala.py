import asyncio
import json

from datetime import datetime, timezone
from forecast.providers.provider import BaseForecastInPointProvider
from forecast.utils.req_interface import RequestInterface, Response
from rich.console import Console
from typing_extensions import override  # for python <3.12

console = Console()


class Vaisala(BaseForecastInPointProvider, RequestInterface):
    def __init__(self, client_id: str, client_secret: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client_id = client_id
        self.client_secret = client_secret

    async def rate_limit_aware_get(self, url: str) -> Response:
        # https://www.xweather.com/docs/weather-api/getting-started/rate-limiting
        resp = Response()

        while not resp.ok:
            resp = await self._native_get(url=url)

            if resp.status != 429:  # Status code for too many requests
                return resp

            time_to_sleep = None

            if resp.headers:
                for key, value in resp.headers.items():
                    if key.lower() == "x-ratelimit-reset-minute":
                        reset_time = datetime.strptime(value, "%a, %d %b %Y %H:%M:%S GMT")
                        reset_time = reset_time.replace(tzinfo=timezone.utc)

                        time_to_sleep = reset_time - datetime.now(timezone.utc)

            if time_to_sleep is not None:
                console.log(f"Rate limit exceeded. Waiting for {time_to_sleep.total_seconds()} seconds.")
                await asyncio.sleep(time_to_sleep.total_seconds())
            else:
                break

        return resp

    @override
    async def get_json_forecast_in_point(self, lon: float, lat: float) -> Response:
        url = f"https://data.api.xweather.com/conditions/{lat},{lon}?filter=minutelyprecip&client_id={self.client_id}&client_secret={self.client_secret}"
        resp = await self.rate_limit_aware_get(url=url)
        if resp.ok:
            resp.payload = json.dumps({
                "position": {
                    "lon": lon,
                    "lat": lat
                },
                "payload": json.loads(resp.payload)
            })

        return resp
