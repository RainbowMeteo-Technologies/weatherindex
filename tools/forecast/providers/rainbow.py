from forecast.providers.provider import BaseForecastInPointProvider
from forecast.utils.req_interface import RequestInterface, Response
from typing_extensions import override  # for python <3.12


class Rainbow(BaseForecastInPointProvider, RequestInterface):
    """
    Rainbow API precip layers:
        - precip provides radars coverage
        - precip-global provides global coverage
    """
    API_PRECIP_LAYERS = ["precip", "precip-global"]

    def __init__(self, token: str, layer: str = "precip", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token = token
        self.layer = layer

    @override
    async def get_json_forecast_in_point(self, lon: float, lat: float) -> Response:
        url = f"https://api.rainbow.ai/nowcast/v1/{self.layer}/{lon}/{lat}?token={self.token}"
        return await self._native_get(url=url)
