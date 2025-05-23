import asyncio
import json
import os

from forecast.client.base import SensorClientBase
from forecast.sensor import Sensor
from rich.console import Console
from typing_extensions import override  # for python <3.12


console = Console()


class MyRadar(SensorClientBase):
    def __init__(self, sub_key: str, sensors: list[Sensor]):
        super().__init__(sensors)
        self.subscription_key = sub_key

    @override
    async def _get_json_forecast_in_point(self, lon: float, lat: float) -> str | bytes | None:
        # https://myradar.developer.azure-api.net/api-details#api=forecast-api&operation=get-forecast-latitude-longitude
        url = f"https://api.myradar.dev/forecast/{lat},{lon}?extend=hourly&units=si&lang=en"
        headers = {
            "Cache-Control": "no-cache",
            "Subscription-Key": self.subscription_key
        }

        return await self._native_get(url=url, headers=headers)
