import json
import os
import typing

from metrics.parse.base_parser import BaseParser
from metrics.utils.precipitation import PrecipitationType

OutputRowType = typing.List[typing.Tuple[str, float, float, int, float, float, int]]

PROB_THRESHOLD = 0.7


class VaisalaParser(BaseParser):
    def _should_parse_file_extension(self, file_extension: str) -> bool:
        """See :func:`~metrics.base_parser.BaseParser._should_parse_file_extension`"""
        return file_extension == ".json"

    def _get_columns(self) -> typing.List[str]:
        """See :func:`~metrics.base_parser.BaseParser._get_columns`"""
        return ["id", "lon", "lat", "timestamp", "precip_rate", "precip_prob", "precip_type"]

    def _parse_impl(self, timestamp: int, file_name: str, data: bytes) -> typing.List[typing.List[any]]:
        """See :func:`~metrics.base_parser.BaseParser._parse_impl`"""
        rows = []
        data_json = json.loads(data)
        sensor_id = os.path.basename(file_name).replace(".json", "")

        if "position" in data_json:
            lon = data_json["position"]["lon"]
            lat = data_json["position"]["lat"]

            data_payload = data_json["payload"]

            if "response" in data_payload and "periods" in data_payload["response"][0]:
                minutely_forecast = data_payload["response"][0]["periods"]

                for item in minutely_forecast:
                    precip_rate = 0.0
                    precip_type = PrecipitationType.UNKNOWN.value
                    precip_prob = 0.0

                    timestamp = item["timestamp"]

                    if "pop" in item:
                        precip_prob = item["pop"]

                    has_rain = item["precipRateMM"] > 0
                    has_snow = item["snowRateCM"] > 0

                    if has_rain and has_snow:
                        precip_type = PrecipitationType.MIX.value
                        precip_rate = max(item["precipRateMM"], item["snowRateCM"] / 10.0)
                    elif has_rain:
                        precip_type = PrecipitationType.RAIN.value
                        precip_rate = item["precipRateMM"]
                    elif has_snow:
                        precip_type = PrecipitationType.SNOW.value
                        precip_rate = item["snowRateCM"] / 10.0

                    rows.append((sensor_id, lon, lat, timestamp, precip_rate, precip_prob, precip_type))

        return rows
