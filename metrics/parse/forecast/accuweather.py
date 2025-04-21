
import json
import os
import typing

from metrics.parse.base_parser import BaseParser
from metrics.utils.precipitation import PrecipitationType


class AccuWeatherParser(BaseParser):

    def _parse_impl(self, timestamp: int, file_name: str, data: bytes) -> typing.List[typing.List[any]]:
        """See :func:`~metrics.base_parser.BaseParser._parse_impl`"""
        rows = []
        data_json = json.loads(data)
        sensor_id = os.path.basename(file_name).replace(".json", "")

        if "position" in data_json:

            payload_json = data_json["payload"]
            lon = data_json["position"]["lon"]
            lat = data_json["position"]["lat"]

            if "Summaries" in payload_json:

                for item in payload_json["Summaries"]:

                    precip_rate = 0.0
                    precip_prob = 0.0
                    precip_type = PrecipitationType.UNKNOWN.value

                    precip_type_name = item["Type"]
                    if precip_type_name is not None:
                        precip_prob = 1.0
                        precip_rate = 10.0  # mm/h
                        precip_type = PrecipitationType.RAIN.value

                        if precip_type_name == "SNOW":
                            precip_type = PrecipitationType.SNOW.value

                    start_time = item["StartMinute"]
                    end_time = item["EndMinute"] + 1
                    for offset in range(start_time, end_time):
                        rows.append((sensor_id, lon, lat, timestamp + offset * 60,
                                    precip_rate, precip_prob, precip_type))
        return rows

    def _should_parse_file_extension(self, file_extension: str) -> bool:
        """See :func:`~metrics.base_parser.BaseParser._should_parse_file_extension`"""
        return file_extension == ".json"

    def _get_columns(self) -> typing.List[str]:
        """See :func:`~metrics.base_parser.BaseParser._get_columns`"""
        return ["id", "lon", "lat", "timestamp", "precip_rate", "precip_prob", "precip_type"]
