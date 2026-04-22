import json

from forecast.providers.provider import BaseForecastInPointProvider
from forecast.utils.req_interface import RequestInterface, Response
from typing_extensions import override  # for python <3.12


class WeatherCompany(BaseForecastInPointProvider, RequestInterface):

    PRODUCT_NAMES = {
        # https://www.ibm.com/docs/en/environmental-intel-suite?topic=apis-short-range-forecast-15-minute
        "forecast-15-minute": ("https://api.weather.com/v3/wx/forecast/fifteenminute?geocode={lat},{lon}"
                               "&units=s&language=en-US&format=json&apiKey={token}"),

        # https://www.ibm.com/docs/en/environmental-intel-suite?topic=apis-short-range-forecast-precipitation-forecast
        "forecast-precipitation": ("https://api.weather.com/v1/geocode/{lat}/{lon}"
                                   "/forecast/precipitation.json?language=en-US&units=s&apiKey={token}")
    }

    def __init__(self, token: str, product_name: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token = token
        self.product_name = product_name
        self.uri_pattern = self.PRODUCT_NAMES[product_name]

    @override
    async def get_json_forecast_in_point(self, lon: float, lat: float) -> Response:
        url = self.uri_pattern.format(lon=lon, lat=lat, token=self.token)
        resp = await self._native_get(url=url)
        if resp.ok:
            resp.payload = json.dumps({
                "position": {
                    "lon": lon,
                    "lat": lat
                },
                "product_name": self.product_name,
                "payload": json.loads(resp.payload)
            })

        return resp
