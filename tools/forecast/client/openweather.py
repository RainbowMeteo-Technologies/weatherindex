import json

from forecast.client.base import SensorClientBase
from forecast.req_interface import Response
from forecast.sensor import Sensor
from typing_extensions import override  # for python <3.12


class OpenWeather(SensorClientBase):

    def __init__(self, token: str, sensors: list[Sensor]):
        super().__init__(sensors)
        self.token = token

    @override
    async def _get_json_forecast_in_point(self, lon: float, lat: float) -> Response:
        # https://openweathermap.org/api/one-call-3#how
        url = f"https://api.openweathermap.org/data/3.0/onecall?lat={lat}&lon={lon}&appid={self.token}"

        resp = await self._native_get(url=url)
        if resp.payload is not None:
            resp.forecast = json.dumps({
                "position": {
                    "lon": lon,
                    "lat": lat
                },
                "payload": json.loads(resp.payload)
            })

        return resp
