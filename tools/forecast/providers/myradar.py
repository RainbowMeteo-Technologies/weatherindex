from forecast.providers.provider import BaseForecastInPointProvider
from forecast.utils.req_interface import RequestInterface

from typing_extensions import override  # for python <3.12


class MyRadar(BaseForecastInPointProvider, RequestInterface):
    def __init__(self, sub_key: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.subscription_key = sub_key

    @override
    async def get_json_forecast_in_point(self, lon: float, lat: float) -> str | bytes | None:
        # https://myradar.developer.azure-api.net/api-details#api=forecast-api&operation=get-forecast-latitude-longitude
        url = f"https://api.myradar.dev/forecast/{lat},{lon}?extend=hourly&units=si&lang=en"
        headers = {
            "Cache-Control": "no-cache",
            "Subscription-Key": self.subscription_key
        }

        return await self._native_get(url=url, headers=headers)
