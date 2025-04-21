import json
import os

from typing import List

from metrics.parse.base_parser import BaseParser

from metrics.utils.precipitation import PrecipitationType


def _convert_precip_type(precip_type: str) -> PrecipitationType:
    if precip_type == "rain":
        return PrecipitationType.RAIN
    elif precip_type == "snow":
        return PrecipitationType.SNOW
    elif precip_type == "mix":
        return PrecipitationType.MIX
    else:
        return PrecipitationType.UNKNOWN


class RainbowAiParser(BaseParser):
    def _parse_impl(self, timestamp: int, file_name: str, data: bytes) -> List[List[any]]:
        """See :func:`~metrics.base_parser.BaseParser._parse_impl`"""
        rows = []

        data_json = json.loads(data)
        sensor_id = os.path.basename(file_name).replace(".json", "")

        lon = data_json["longitude"]
        lat = data_json["latitude"]

        forecasts = data_json["forecast"]

        for forecast in forecasts:
            timestamp = forecast["timestampEnd"]
            precip_rate = forecast["precipRate"]
            precip_type = _convert_precip_type(forecast["precipType"])
            precip_prob = 1.0

            rows.append((sensor_id, lon, lat, timestamp, precip_rate, precip_prob, precip_type.value))

        return rows

    def _should_parse_file_extension(self, file_extension: str) -> bool:
        """See :func:`~metrics.base_parser.BaseParser._should_parse_file_extension`"""
        return file_extension == ".json"

    def _get_columns(self) -> List[str]:
        """See :func:`~metrics.base_parser.BaseParser._get_columns`"""
        return ["id", "lon", "lat", "timestamp", "precip_rate", "precip_prob", "precip_type"]
