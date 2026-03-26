from forecast.providers.provider import BaseForecastInPointProvider
from forecast.utils.req_interface import RequestInterface, Response
from typing_extensions import override  # for python <3.12


class Rainbow(BaseForecastInPointProvider, RequestInterface):
    """
    Rainbow API versions:
        - v1 provides radars coverage
        - v2 provides global coverage
    """
    API_VERSIONS = ["v1", "v2"]

    def __init__(self, token: str, version: str = "v1", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token = token
        self.version = version

    @override
    async def get_json_forecast_in_point(self, lon: float, lat: float) -> Response:
        url = f"https://api.rainbow.ai/nowcast/{self.version}/precip/{lon}/{lat}?token={self.token}"
        return await self._native_get(url=url)
