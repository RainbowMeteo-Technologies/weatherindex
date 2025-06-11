import asyncio
import json
import os

from forecast.client.base import SensorClientBase
from forecast.req_interface import Response
from forecast.sensor import Sensor
from rich.console import Console
from typing_extensions import override  # for python <3.12


console = Console()


class Microsoft(SensorClientBase):
    def __init__(self, client_id: str, subscription_key: str, sensors: list[Sensor]):
        super().__init__(sensors)
        self.client_id = client_id
        self.subscription_key = subscription_key

    @override
    async def _get_json_forecast_in_point(self, lon: float, lat: float) -> Response:
        # https://learn.microsoft.com/en-us/rest/api/maps/weather/get-minute-forecast?view=rest-maps-2023-06-01&tabs=HTTP
        url = (f"https://atlas.microsoft.com/weather/forecast/minute/json?api-version=1.1"
               f"&query={lat},{lon}&interval=1&subscription-key={self.subscription_key}")

        headers = {
            "x-ms-client-id": self.client_id
        }

        resp = await self._native_get(url=url, headers=headers)
        if resp.ok:
            resp.payload = json.dumps({
                "position": {
                    "lon": lon,
                    "lat": lat
                },
                "payload": json.loads(resp.payload)
            })

        return resp
