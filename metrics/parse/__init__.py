from metrics.data_vendor import DataVendor

from metrics.parse.forecast.accuweather import AccuWeatherParser
from metrics.parse.forecast.rainbow import RainbowAiParser
from metrics.parse.forecast.tomorrow_io import TomorrowIoParser
from metrics.parse.forecast.vaisala import VaisalaParser
from metrics.parse.forecast.weather_company import WeatherCompanyParser
from metrics.parse.forecast.weather_kit import WeatherKitParser
from metrics.parse.observation.metar import MetarParser

PROVIDERS_PARSERS = {
    DataVendor.AccuWeather: AccuWeatherParser,
    DataVendor.WeatherKit: WeatherKitParser,
    DataVendor.TomorrowIo: TomorrowIoParser,
    DataVendor.Vaisala: VaisalaParser,
    DataVendor.RainbowAi: RainbowAiParser,
    DataVendor.WeatherCompany: WeatherCompanyParser,

    DataVendor.Metar: MetarParser,
}
