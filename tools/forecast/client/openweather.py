import json

from forecast.client.base import SensorClientBase
from forecast.sensor import Sensor
from typing_extensions import override  # for python <3.12


class OpenWeather(SensorClientBase):

    def __init__(self, token: str, sensors: list[Sensor]):
        super().__init__(sensors)
        self.token = token

    @override
    async def _get_json_forecast_in_point(self, lon: float, lat: float) -> str | bytes | None:
        # https://openweathermap.org/api/one-call-3#how
        url = f"https://api.openweathermap.org/data/3.0/onecall?lat={lat}&lon={lon}&appid={self.token}"

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
