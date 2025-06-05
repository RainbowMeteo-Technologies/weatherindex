import asyncio
import json
import os

from forecast.client.base import SensorClientBase
from forecast.req_interface import Response
from forecast.sensor import Sensor
from rich.console import Console
from typing_extensions import override  # for python <3.12


console = Console()


class Vaisala(SensorClientBase):
    def __init__(self, client_id: str, client_secret: str, sensors: list[Sensor]):
        super().__init__(sensors)
        self.client_id = client_id
        self.client_secret = client_secret

    @override
    async def _get_json_forecast_in_point(self, lon: float, lat: float) -> Response:
        url = (f"https://data.api.xweather.com/conditions/{lat},{lon}?filter=minutelyprecip"
               f"&client_id={self.client_id}&client_secret={self.client_secret}")
        resp = await self._native_get(url=url)
        if resp.payload is not None:

            resp.forecast = json.dumps({
                "position": {
                    "lon": lon,
                    "lat": lat
                },
                "payload": json.loads(resp.payload)
            })

        return resp
