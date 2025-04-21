import asyncio
import json
import os

from concurrent.futures import ThreadPoolExecutor
from typing import List

from forecast.req_interface import RequestInterface
from forecast.sensor import Sensor

from rich.console import Console

console = Console()


TOMORROW_FORECAST_TYPES = ["hour", "6hours"]


class TomorrowIo(RequestInterface):
    def __init__(self, token: str, forecast_type: str, sensors: List[Sensor]):
        self.token = token
        self.forecast_type = forecast_type
        self.sensors = sensors

    def _request_1hour_forecast(self, lon: float, lat: float):
        # https://docs.tomorrow.io/reference/weather-forecast
        url = f"https://api.tomorrow.io/v4/weather/forecast?timesteps=1m&location={lat},{lon}&apikey={self.token}"

        headers = {
            "accept": "application/json"
        }

        return self._native_get(url=url, headers=headers)

    def _request_6hours_forecast(self, lon: float, lat: float):
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

        return self._native_post(url, headers=headers, body=payload)

    async def _get_json_forecast_in_point(self, lon: float, lat: float):
        data = None
        if self.forecast_type == "hour":
            data = self._request_1hour_forecast(lon=lon, lat=lat)
        elif self.forecast_type == "6hours":
            data = self._request_6hours_forecast(lon=lon, lat=lat)

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
