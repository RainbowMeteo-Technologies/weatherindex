import os

from forecast.providers.provider import BaseForecastInPointProvider
from forecast.utils.req_interface import RequestInterface, Response
from typing_extensions import override  # for python <3.12


class Rainbow(BaseForecastInPointProvider, RequestInterface):
    """
    Rainbow API products:
        - nowcast-precip provides nowcast for radars coverage
        - nowcast-precip-global provides nowcast for global coverage
        - forecast-weather provides weather variables forecast globally
    """
    RAINBOW_API_BASE_URL = os.getenv("RAINBOW_API_BASE_URL", "https://api.rainbow.ai")

    _API_PRODUCT_ENDPOINT_MAPPING = {
        "nowcast-precip": "nowcast/v1/precip",
        "nowcast-precip-global": "nowcast/v1/precip-global",
        "forecast-weather": "weather/v1/forecast"
    }

    API_PRODUCTS = list(_API_PRODUCT_ENDPOINT_MAPPING.keys())

    def __init__(self, token: str, product: str = "nowcast-precip", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token = token
        self.endpoint = self._API_PRODUCT_ENDPOINT_MAPPING[product]

    def _get_location_url(self, lon: float, lat: float) -> str:
        loc_endpoint = os.path.join(self.RAINBOW_API_BASE_URL, self.endpoint, str(lon), str(lat))
        return f"{loc_endpoint}?token={self.token}"

    @override
    async def get_json_forecast_in_point(self, lon: float, lat: float) -> Response:
        return await self._native_get(url=self.get_location_url(lon, lat))
