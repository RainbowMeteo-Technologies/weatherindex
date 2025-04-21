import asyncio
import json
import os

from concurrent.futures import ThreadPoolExecutor
from typing import List

from forecast.req_interface import RequestInterface
from forecast.sensor import Sensor

from rich.console import Console

console = Console()


class MyRadar(RequestInterface):
    def __init__(self, sub_key: str, sensors: List[Sensor]):
        self.subscription_key = sub_key
        self.sensors = sensors

    async def _get_json_forecast_in_point(self, lon: float, lat: float):
        # https://myradar.developer.azure-api.net/api-details#api=forecast-api&operation=get-forecast-latitude-longitude
        url = f"https://api.myradar.dev/forecast/{lat},{lon}?extend=hourly&units=si&lang=en"
        headers = {
            "Cache-Control": "no-cache",
            "Subscription-Key": self.subscription_key
        }

        return self._native_get(url=url, headers=headers)

    async def get_forecast(self, download_path: str, process_num: int = None):
        with ThreadPoolExecutor(max_workers=process_num) as executor:
            loop = asyncio.get_event_loop()

            tasks = []
            for sensor in self.sensors:
                task = loop.run_in_executor(executor, self._get_json_forecast_in_point, sensor.lon, sensor.lat)
                tasks.append(task)

            console.log(f"Downloading {len(tasks)} forecasts...")
            forecasts = await asyncio.gather(*tasks)

            for forecast, sensor in zip(forecasts, self.sensors):
                if forecast is not None:
                    with open(os.path.join(download_path, f"{sensor.id}.json"), "w") as file:
                        file.write(forecast)
                else:
                    console.log(f"Wasn't able to get data for {sensor.id}")
