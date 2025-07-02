import json

from forecast.providers.provider import BaseForecastInPointProvider
from forecast.utils.req_interface import RequestInterface, Response
from typing_extensions import override  # for python <3.12


TOMORROW_FORECAST_TYPES = ["hour", "6hours"]


class TomorrowIo(BaseForecastInPointProvider, RequestInterface):
    def __init__(self, token: str, forecast_type: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token = token
        self.forecast_type = forecast_type

    async def _request_1hour_forecast(self, lon: float, lat: float) -> Response:
        # https://docs.tomorrow.io/reference/weather-forecast
        url = f"https://api.tomorrow.io/v4/weather/forecast?timesteps=1m&location={lat},{lon}&apikey={self.token}"

        headers = {
            "accept": "application/json"
        }

        return await self._native_get(url=url, headers=headers)

    async def _request_6hours_forecast(self, lon: float, lat: float) -> Response:
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

        return await self._native_post(url, headers=headers, body=payload)

    @override
    async def get_json_forecast_in_point(self, lon: float, lat: float) -> Response:
        if self.forecast_type == "hour":
            resp = await self._request_1hour_forecast(lon=lon, lat=lat)
        elif self.forecast_type == "6hours":
            resp = await self._request_6hours_forecast(lon=lon, lat=lat)
        else:
            resp = Response()

        if resp.ok:
            resp.payload = json.dumps({
                "position": {
                    "lon": lon,
                    "lat": lat
                },
                "payload": json.loads(resp.payload)
            })
        return resp
