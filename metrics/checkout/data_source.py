from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class ForecastSourcesInfo:
    s3_uri_rainviewer: Optional[str] = None
    s3_uri_wk: Optional[str] = None
    s3_uri_accuweather: Optional[str] = None
    s3_uri_tomorrowio: Optional[str] = None
    s3_uri_vaisala: Optional[str] = None
    s3_uri_rainbowai: Optional[str] = None
    s3_uri_weathercompany: Optional[str] = None


@dataclass
class ObservationSourcesInfo:
    s3_uri_metar: Optional[str] = None


def _timestamp_zip(timestamp: int) -> str:
    return f"{timestamp}.zip"


@dataclass
class DataSource:
    vendor: str                          # name of the data source vendor (used only for logging)
    s3_uri: str                          # s3 uri of the folder where to download data
    data_folder: str                     # the folder where to store downloaded data
    period: str                          # period of the data archives stores in s3
    filename_rule: Callable[[int], str]  # rule to convert timestamp to filename

    @staticmethod
    def create(vendor: str, s3_uri: str, data_folder: str, period: str) -> "DataSource":
        return DataSource(vendor=vendor,
                          s3_uri=s3_uri,
                          data_folder=data_folder,
                          period=period,
                          filename_rule=_timestamp_zip)
