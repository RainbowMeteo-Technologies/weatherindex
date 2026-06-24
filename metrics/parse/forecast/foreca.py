import json
import os
import typing

from datetime import datetime
from metrics.parse.base_parser import BaseParser
from metrics.utils.precipitation import PrecipitationType


def _parse_precip_type(precip_type: typing.Optional[str], precip_rate: float, snow_rate: float) -> int:
    if precip_type == "rain":
        return PrecipitationType.RAIN.value
    elif precip_type == "snow":
        return PrecipitationType.SNOW.value
    elif precip_type == "mixed":
        return PrecipitationType.MIX.value
    elif precip_rate > 0 and snow_rate > 0:
        return PrecipitationType.MIX.value
    elif snow_rate > 0:
        return PrecipitationType.SNOW.value
    elif precip_rate > 0:
        return PrecipitationType.RAIN.value
    return PrecipitationType.UNKNOWN.value


class ForecaParser(BaseParser):

    def _parse_impl(self, timestamp: int, file_name: str, data: bytes) -> typing.List[typing.List[any]]:
        rows = []
        data_json = json.loads(data)
        sensor_id = os.path.basename(file_name).replace(".json", "")

        if "position" not in data_json:
            return rows

        lon = data_json["position"]["lon"]
        lat = data_json["position"]["lat"]

        for item in data_json.get("payload", {}).get("forecast", []):
            item_timestamp = int(datetime.fromisoformat(item["time"]).timestamp())
            precip_rate = float(item.get("precipRate", 0.0))
            snow_rate = float(item.get("snowRate", 0.0))
            precip_prob = item.get("precipProb", 0) / 100.0
            precip_type = _parse_precip_type(item.get("precipType"), precip_rate, snow_rate)
            effective_rate = max(precip_rate, snow_rate)

            rows.append((sensor_id, lon, lat, item_timestamp, effective_rate, precip_prob, precip_type))

        return rows

    def _should_parse_file_extension(self, file_extension: str) -> bool:
        return file_extension == ".json"

    def _get_columns(self) -> typing.List[str]:
        return ["id", "lon", "lat", "timestamp", "precip_rate", "precip_prob", "precip_type"]
