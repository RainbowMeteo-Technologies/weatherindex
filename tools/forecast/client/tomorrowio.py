import asyncio
import json
import os

from forecast.client.base import SensorClientBase
from forecast.sensor import Sensor
from rich.console import Console
from typing_extensions import override  # for python <3.12


console = Console()


TOMORROW_FORECAST_TYPES = ["hour", "6hours"]


class TomorrowIo(SensorClientBase):
    def __init__(self, token: str, forecast_type: str, sensors: list[Sensor]):
        super().__init__(sensors)
        self.token = token
        self.forecast_type = forecast_type

    async def _request_1hour_forecast(self, lon: float, lat: float) -> bytes | None:
        # https://docs.tomorrow.io/reference/weather-forecast
        url = f"https://api.tomorrow.io/v4/weather/forecast?timesteps=1m&location={lat},{lon}&apikey={self.token}"

        headers = {
            "accept": "application/json"
        }

        return await self._native_get(url=url, headers=headers)

    async def _request_6hours_forecast(self, lon: float, lat: float) -> bytes | None:
        # https://docs.tomorrow.io/reference/post-timelines
        url = f"https://api.tomorrow.io/v4/timelines?apikey={self.token}"

        payload = {
            "location": f"{lat}, {lon}",
            "fields": ["temperature", "rainIntensity", "snowIntensity", "sleetIntensity", "precipitationProbability"],
            "units": "metric",
            "timesteps": ["1m"],
            "startTime": "now",
            "endTime": "nowPlus6h"
        }
        headers = {
            "accept": "application/json",
            "Accept-Encoding": "gzip",
            "content-type": "application/json"
        }

        return await self._native_post(url, headers=headers, body=payload)

    @override
    async def _get_json_forecast_in_point(self, lon: float, lat: float) -> str | bytes | None:
        data = None
        if self.forecast_type == "hour":
            data = await self._request_1hour_forecast(lon=lon, lat=lat)
        elif self.forecast_type == "6hours":
            data = await self._request_6hours_forecast(lon=lon, lat=lat)

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
