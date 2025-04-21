from enum import Enum


class BaseDataVendor:
    pass


class DataVendor(BaseDataVendor, Enum):
    WeatherKit = "weatherkit"
    AccuWeather = "accuweather"
    TomorrowIo = "tomorrowio"
    Vaisala = "vaisala"
    RainbowAi = "rainbowai"
    RainViewer = "rainviewer"
    WeatherCompany = "weathercompany"

    Metar = "metar"
