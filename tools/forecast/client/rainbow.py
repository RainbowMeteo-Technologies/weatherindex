import asyncio
import os
from typing import List
from concurrent.futures import ThreadPoolExecutor

from forecast.req_interface import RequestInterface
from forecast.sensor import Sensor

from rich.console import Console

console = Console()


class Rainbow(RequestInterface):
    def __init__(self, token: str, sensors: List[Sensor]):
        self.token = token
        self.sensors = sensors

    def _get_json_forecast_in_point(self, lon: float, lat: float):
        url = f"https://api.rainbow.ai/nowcast/v1/precip/{lon}/{lat}?token={self.token}"
        return self._native_get(url=url)

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
                    with open(os.path.join(download_path, f"{sensor.id}.json"), "wb") as file:
                        file.write(forecast)
                else:
                    console.log(f"Wasn't able to get data for {sensor.id}")
