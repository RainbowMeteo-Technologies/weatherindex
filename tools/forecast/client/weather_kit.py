import asyncio
import json
import os
import jwt

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from typing import BinaryIO, List

from forecast.req_interface import RequestInterface
from forecast.sensor import Sensor

from rich.console import Console

console = Console()


@dataclass(frozen=True)
class TokenParams:
    team_id: str
    service_id: str
    key_id: str
    private_key_path: str
    expire_time: int = 3600

    @staticmethod
    def from_json(json_file: BinaryIO) -> "TokenParams":
        config = json.loads(json_file.read())

        return TokenParams(team_id=config["team_id"],
                           service_id=config["service_id"],
                           key_id=config["key_id"],
                           private_key_path=config["private_key_path"],
                           expire_time=config["expire_time"])


@dataclass(frozen=True)
class Token:
    """
    Attributes
    ----------
    token : str
        Token value
    expire_timestamp : int
        UTC timestamp when token expires
    """
    token: str
    expire_timestamp: int

    @staticmethod
    def generate(params: TokenParams) -> "Token":
        with open(params.private_key_path, "r") as key_file:
            private_key = key_file.read()

        current_time = int(datetime.now().timestamp())
        expiry_time = current_time + params.expire_time
        payload = {
            "iss": params.team_id,
            "iat": current_time,
            "exp": expiry_time,
            "sub": params.service_id
        }

        headers = {
            "alg": "ES256",
            "kid": params.key_id,
            "id": f"{params.team_id}.{params.service_id}"
        }

        token = jwt.encode(payload, private_key, algorithm="ES256", headers=headers)
        return Token(token, expiry_time)


class WeatherKit(RequestInterface):
    def __init__(self, token: str, datasets: str, sensors: List[Sensor]):
        self.token = token
        self.datasets = datasets
        self.sensors = sensors

    def _get_json_forecast_in_point(self, lon: float, lat: float) -> bytes:
        # https://developer.apple.com/documentation/weatherkitrestapi/get_api_v1_weather_language_latitude_longitude
        url = f"https://weatherkit.apple.com/api/v1/weather/en/{lat}/{lon}/"
        headers = {
            "Authorization": f"Bearer {self.token}"
        }

        params = {
            "timezone": "utc",
            "dataSets": self.datasets,
        }

        return self._native_get(url=url, params=params, headers=headers)

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
