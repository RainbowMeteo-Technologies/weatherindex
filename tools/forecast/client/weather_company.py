import asyncio
import json
import os

from forecast.client.base import SensorClientBase
from forecast.sensor import Sensor
from rich.console import Console
from typing_extensions import override  # for python <3.12


console = Console()


class WeatherCompany(SensorClientBase):

    def __init__(self, token: str, sensors: list[Sensor]):
        super().__init__(sensors)
        self.token = token

    @override
    async def _get_json_forecast_in_point(self, lon: float, lat: float) -> str | bytes | None:
        url = f"https://api.weather.com/v3/wx/forecast/fifteenminute?geocode={lat},{lon}&units=s&language=en-US&format=json&apiKey={self.token}"
        data = await self._native_get(url=url)
        if data is not None:
            payload = json.loads(data)

            return json.dumps({
                "position": {
                    "lon": lon,
                    "lat": lat
                },
                "payload": payload
            })

        return None
