import asyncio
import json
import jwt
import os

from dataclasses import dataclass
from datetime import datetime
from forecast.client.base import SensorClientBase
from forecast.sensor import Sensor
from rich.console import Console
from typing import BinaryIO
from typing_extensions import override  # for python <3.12


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


class WeatherKit(SensorClientBase):
    def __init__(self, token: str, datasets: str, sensors: list[Sensor]):
        super().__init__(sensors)
        self.token = token
        self.datasets = datasets

    @override
    async def _get_json_forecast_in_point(self, lon: float, lat: float) -> str | bytes | None:
        # https://developer.apple.com/documentation/weatherkitrestapi/get_api_v1_weather_language_latitude_longitude
        url = f"https://weatherkit.apple.com/api/v1/weather/en/{lat}/{lon}/"
        headers = {
            "Authorization": f"Bearer {self.token}"
        }

        params = {
            "timezone": "utc",
            "dataSets": self.datasets,
        }

        return await self._native_get(url=url, params=params, headers=headers)
