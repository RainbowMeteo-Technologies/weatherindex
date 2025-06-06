import asyncio
import json
import os

from forecast.client.base import SensorClientBase
from forecast.req_interface import Response
from forecast.sensor import Sensor
from rich.console import Console
from typing_extensions import override  # for python <3.12


console = Console()


class AccuWeather(SensorClientBase):

    def __init__(self, token: str, sensors: list[Sensor]):
        super().__init__(sensors)
        self.token = token

    @override
    async def _get_json_forecast_in_point(self, lon: float, lat: float) -> Response:
        url = f"http://dataservice.accuweather.com/forecasts/v1/minute?q={lat},{lon}&apikey={self.token}"
        resp = await self._native_get(url=url)
        if resp.ok:
            resp.payload = json.dumps({
                "position": {
                    "lon": lon,
                    "lat": lat
                },
                "payload": json.loads(resp.payload)
            })
        return resp
