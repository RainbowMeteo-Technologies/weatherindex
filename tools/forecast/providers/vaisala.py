import json

from forecast.providers.provider import BaseForecastInPointProvider
from forecast.utils.req_interface import RequestInterface

from typing_extensions import override  # for python <3.12


class Vaisala(BaseForecastInPointProvider, RequestInterface):
    def __init__(self, client_id: str, client_secret: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client_id = client_id
        self.client_secret = client_secret

    @override
    async def get_json_forecast_in_point(self, lon: float, lat: float) -> str | bytes | None:
        url = f"https://data.api.xweather.com/conditions/{lat},{lon}?filter=minutelyprecip&client_id={self.client_id}&client_secret={self.client_secret}"
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
