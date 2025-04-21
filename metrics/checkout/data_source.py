import datetime
import metrics.checkout.constants as constants
import os
import typing

from dataclasses import dataclass
from metrics.data_vendor import DataVendor
from metrics.session import Session


@dataclass
class ForecastSourcesInfo:
    s3_uri_rainviewer: typing.Optional[str] = None
    s3_uri_wk: typing.Optional[str] = None
    s3_uri_accuweather: typing.Optional[str] = None
    s3_uri_tomorrowio: typing.Optional[str] = None
    s3_uri_vaisala: typing.Optional[str] = None
    s3_uri_rainbowai: typing.Optional[str] = None
    s3_uri_weathercompany: typing.Optional[str] = None


@dataclass
class ObservationSourcesInfo:
    s3_uri_metar: typing.Optional[str] = None


def _timestamp_zip(timestamp: int) -> str:
    return f"{timestamp}.zip"


FILENAME_RULES = {
    "timestamp": _timestamp_zip,
}


@dataclass
class DataSource:
    vendor: str                         # name of the data source vendor (used only for logging)
    s3_uri: str                         # s3 uri of the folder where to download data
    data_folder: str                    # the folder where to store downloaded data
    period: str                         # period of the data archives stores in s3
    filename_rule: str = "timestamp"    # rule to convert timestamp to filename

    @staticmethod
    def forecast_sources_list(session: Session, forecast_source_info: ForecastSourcesInfo) -> typing.List["DataSource"]:
        return [
            DataSource(vendor="weather kit", s3_uri=forecast_source_info.s3_uri_wk,
                       data_folder=os.path.join(session.data_folder, DataVendor.WeatherKit.value),
                       period=constants.WEATHERKIT_PERIOD),
            DataSource(vendor="accuweather", s3_uri=forecast_source_info.s3_uri_accuweather,
                       data_folder=os.path.join(session.data_folder, DataVendor.AccuWeather.value),
                       period=constants.ACCUWEATHER_PERIOD),
            DataSource(vendor="rainviewer", s3_uri=forecast_source_info.s3_uri_rainviewer,
                       data_folder=os.path.join(session.data_folder, DataVendor.RainViewer.value),
                       period=constants.RAINVIEWER_PERIOD),
            DataSource(vendor="tomorrow-io", s3_uri=forecast_source_info.s3_uri_tomorrowio,
                       data_folder=os.path.join(session.data_folder, DataVendor.TomorrowIo.value), period=constants.TOMORROWIO_PERIOD),
            DataSource(vendor="vaisala", s3_uri=forecast_source_info.s3_uri_vaisala,
                       data_folder=os.path.join(session.data_folder, DataVendor.Vaisala.value), period=constants.VAISALA_PERIOD),
            DataSource(vendor="rainbowai", s3_uri=forecast_source_info.s3_uri_rainbowai,
                       data_folder=os.path.join(session.data_folder, DataVendor.RainbowAi.value), period=constants.RAINBOWAI_PERIOD),
            DataSource(vendor="weathercompany", s3_uri=forecast_source_info.s3_uri_weathercompany,
                       data_folder=os.path.join(session.data_folder, DataVendor.WeatherCompany.value), period=constants.WEATHERCOMPANY_PERIOD),
        ]

    @staticmethod
    def observation_sources_list(session: Session,
                                 observation_source_info: ObservationSourcesInfo) -> typing.List["DataSource"]:
        return [
            DataSource(vendor="metar", s3_uri=observation_source_info.s3_uri_metar,
                       data_folder=os.path.join(session.data_folder, DataVendor.Metar.value),
                       period=constants.METAR_PERIOD)
        ]
