from forecast.providers.provider import BaseForecastInPointProvider
from forecast.utils.req_interface import RequestInterface, Response
from typing_extensions import override  # for python <3.12


class Rainbow(BaseForecastInPointProvider, RequestInterface):

    def __init__(self, token: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token = token

    @override
    async def get_json_forecast_in_point(self, lon: float, lat: float) -> Response:
        url = f"https://api.rainbow.ai/nowcast/v1/precip/{lon}/{lat}?token={self.token}"
        resp = await self._native_get(url=url)

        if resp.ok and len(resp.payload) == 0:
            resp.set_failed()

        return resp
