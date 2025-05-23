import asyncio
import os

from forecast.client.base import SensorClientBase
from forecast.sensor import Sensor
from rich.console import Console
from typing_extensions import override  # for python <3.12


console = Console()


class Rainbow(SensorClientBase):

    def __init__(self, token: str, sensors: list[Sensor]):
        super().__init__(sensors)
        self.token = token

    @override
    async def _get_json_forecast_in_point(self, lon: float, lat: float) -> str | bytes | None:
        url = f"https://api.rainbow.ai/nowcast/v1/precip/{lon}/{lat}?token={self.token}"
        return await self._native_get(url=url)
