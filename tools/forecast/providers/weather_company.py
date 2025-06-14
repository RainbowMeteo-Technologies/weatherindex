import json

from forecast.providers.provider import BaseForecastInPointProvider
from forecast.utils.req_interface import RequestInterface

from typing_extensions import override  # for python <3.12


class WeatherCompany(BaseForecastInPointProvider, RequestInterface):

    def __init__(self, token: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token = token

    @override
    async def get_json_forecast_in_point(self, lon: float, lat: float) -> str | bytes | None:
        url = f"https://api.weather.com/v3/wx/forecast/fifteenminute?geocode={lat},{lon}&units=s&language=en-US&format=json&apiKey={self.token}"
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
