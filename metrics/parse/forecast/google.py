import json
import os
import typing

from dateutil.parser import isoparse
from metrics.parse.base_parser import BaseParser
from metrics.utils.precipitation import PrecipitationType

FORECAST_HORIZON = 3600  # segments starting later than this (seconds) after the snapshot are dropped

_PRECIP_TYPES = {
    "RAIN": PrecipitationType.RAIN.value,
    "SNOW": PrecipitationType.SNOW.value,
    "HAIL": PrecipitationType.RAIN.value,
}


def _parse_time(time_str: str) -> int:
    return int(isoparse(time_str).timestamp())


def _parse_quantity(segment: typing.Dict[str, any], key: str) -> float:
    value = segment.get(key) or {}
    return float(value.get("quantity", 0.0) or 0.0)


class GoogleParser(BaseParser):

    def _parse_impl(self, timestamp: int, file_name: str, data: bytes) -> typing.List[typing.List[any]]:
        """See :func:`~metrics.base_parser.BaseParser._parse_impl`"""
        rows = []
        data_json = json.loads(data)
        sensor_id = os.path.basename(file_name).replace(".json", "")

        if "position" not in data_json:
            return rows

        lon = data_json["position"]["lon"]
        lat = data_json["position"]["lat"]

        payload = data_json.get("payload") or {}

        for segment in payload.get("segments", []):
            time_frame = segment.get("timeFrame") or {}
            if "startTime" not in time_frame or "endTime" not in time_frame:
                continue

            start_time = _parse_time(time_frame["startTime"])
            end_time = _parse_time(time_frame["endTime"])

            if start_time > timestamp + FORECAST_HORIZON:
                continue

            duration = end_time - start_time
            if duration <= 0:
                continue

            amount = max(_parse_quantity(segment, "qpf"), _parse_quantity(segment, "snowfallAmount"))
            precip_rate = amount / duration * 3600.0
            precip_prob = (segment.get("probability") or 0) / 100.0
            precip_type = _PRECIP_TYPES.get(segment.get("type"), PrecipitationType.UNKNOWN.value)

            rows.append((sensor_id, lon, lat, start_time, precip_rate, precip_prob, precip_type))

        return rows

    def _should_parse_file_extension(self, file_extension: str) -> bool:
        """See :func:`~metrics.base_parser.BaseParser._should_parse_file_extension`"""
        return file_extension == ".json"

    def _get_columns(self) -> typing.List[str]:
        """See :func:`~metrics.base_parser.BaseParser._get_columns`"""
        return ["id", "lon", "lat", "timestamp", "precip_rate", "precip_prob", "precip_type"]
