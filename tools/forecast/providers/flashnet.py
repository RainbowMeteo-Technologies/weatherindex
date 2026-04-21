from forecast.providers.provider import BaseForecastInPointProvider
from forecast.utils.req_interface import RequestInterface, Response
from typing_extensions import override  # for python <3.12


class FlashNet(BaseForecastInPointProvider, RequestInterface):
    """
    FlashNet point-forecast provider.
    Polls the FlashNet Benchmark API for precipitation nowcasts.
    """

    DEFAULT_API_URL = (
        "https://benchmark-api-935480850831.europe-west3.run.app"
    )

    def __init__(self, api_url: str = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_url = api_url or self.DEFAULT_API_URL

    @override
    async def get_json_forecast_in_point(self, lon: float, lat: float) -> Response:
        url = f"{self.api_url}/nowcast/v1/precip?lon={lon}&lat={lat}"
        return await self._native_get(url=url)
