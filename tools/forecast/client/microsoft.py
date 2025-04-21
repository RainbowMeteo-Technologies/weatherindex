import asyncio
import json
import os

from concurrent.futures import ThreadPoolExecutor
from typing import List

from forecast.req_interface import RequestInterface
from forecast.sensor import Sensor

from rich.console import Console

console = Console()


class Microsoft(RequestInterface):
    def __init__(self, client_id: str, subscription_key: str, sensors: List[Sensor]):
        self.client_id = client_id
        self.subscription_key = subscription_key
        self.sensors = sensors

    async def _get_json_forecast_in_point(self, lon: float, lat: float):
        # https://learn.microsoft.com/en-us/rest/api/maps/weather/get-minute-forecast?view=rest-maps-2023-06-01&tabs=HTTP
        url = f"https://atlas.microsoft.com/weather/forecast/minute/json?api-version=1.1&query={lat},{lon}&interval=1&subscription-key={self.subscription_key}"
        headers = {
            "x-ms-client-id": self.client_id
        }

        data = self._native_get(url=url, headers=headers)
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
