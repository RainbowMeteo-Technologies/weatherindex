import json
import os

from forecast.providers.provider import BaseRateLimitedForecastInPointProvider
from forecast.utils.req_interface import RequestInterface, Response
from typing_extensions import override  # for python <3.12


class Foreca(BaseRateLimitedForecastInPointProvider, RequestInterface):

    FORECA_API_BASE_URL = os.getenv("FORECA_API_BASE_URL", "https://weatherapi.foreca.net")

    _API_PRODUCT_ENDPOINT_MAPPING = {
        "nowcast-short": "api/v1/forecast/minutely",
        "nowcast-long": "api/v1/forecast/15minutely"
    }

    API_PRODUCTS = list(_API_PRODUCT_ENDPOINT_MAPPING.keys())

    def __init__(self, token: str, product: str = "nowcast-long", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token = token
        self.endpoint = self._API_PRODUCT_ENDPOINT_MAPPING[product]

    def _get_location_url(self, lon: float, lat: float) -> str:
        return os.path.join(self.FORECA_API_BASE_URL, self.endpoint, f"{lon},{lat}")

    @override
    async def get_json_forecast_in_point(self, lon: float, lat: float) -> Response:
        resp = await self._native_get(url=self._get_location_url(lon, lat),
                                      headers={"Authorization": f"Bearer {self.token}"})
        if resp.ok:
            resp.payload = json.dumps({
                "position": {
                    "lon": lon,
                    "lat": lat
                },
                "payload": json.loads(resp.payload)
            })
        return resp
