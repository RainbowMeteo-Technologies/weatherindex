
import json
import os
import typing

from dateutil.parser import isoparse
from metrics.parse.base_parser import BaseParser
from metrics.utils.precipitation import PrecipitationType

OutputRowType = typing.List[typing.Tuple[str, float, float, int, float, float, int]]

PROB_THRESHOLD = 0.7


def _parse_time(time_str: str) -> int:
    return int(isoparse(time_str).timestamp())


class TomorrowIoParser(BaseParser):

    def _parse_impl(self, timestamp: int, file_name: str, data: bytes) -> typing.List[typing.List[any]]:
        """See :func:`~metrics.base_parser.BaseParser._parse_impl`"""
        rows = []
        data_json = json.loads(data)
        sensor_id = os.path.basename(file_name).replace(".json", "")

        if "position" in data_json:
            lon = data_json["position"]["lon"]
            lat = data_json["position"]["lat"]

            data_payload = data_json["payload"]

            if "data" in data_payload:
                data_payload = data_payload["data"]

            if "timelines" not in data_payload:
                return rows

            data_timelines = data_payload["timelines"]

            timestamp_prop = None
            minutely_forecast = None
            # 6hours timelines
            if isinstance(data_timelines, list) and "intervals" in data_timelines[0]:
                timestamp_prop = "startTime"
                minutely_forecast = data_timelines[0]["intervals"]
            # regular 1hour forecast endpoint
            elif "minutely" in data_payload["timelines"]:
                timestamp_prop = "time"
                minutely_forecast = data_timelines["minutely"]

            if timestamp_prop is None:
                return rows

            for item in minutely_forecast:
                timestamp = _parse_time(item[timestamp_prop])

                values = item["values"]

                precip_rate = 0.0
                precip_type = PrecipitationType.UNKNOWN.value

                precip_prob = values["precipitationProbability"] / 100.0

                has_rain = "rainIntensity" in values and values["rainIntensity"] > 0
                has_snow = "snowIntensity" in values and values["snowIntensity"] > 0
                has_mix = "sleetIntensity" in values and values["sleetIntensity"] > 0

                if has_rain:
                    precip_rate = values["rainIntensity"]
                    precip_type = PrecipitationType.RAIN.value
                elif has_snow:
                    precip_rate = values["snowIntensity"]
                    precip_type = PrecipitationType.SNOW.value
                elif has_mix:
                    precip_rate = values["sleetIntensity"]
                    precip_type = PrecipitationType.MIX.value
                # NOTE: decide how to treat freezing rain
                # elif values["freezingRainIntensity"] > 0:

                rows.append((sensor_id, lon, lat, timestamp, precip_rate, precip_prob, precip_type))

        return rows

    def _should_parse_file_extension(self, file_extension: str) -> bool:
        """See :func:`~metrics.base_parser.BaseParser._should_parse_file_extension`"""
        return file_extension == ".json"

    def _get_columns(self) -> typing.List[str]:
        """See :func:`~metrics.base_parser.BaseParser._get_columns`"""
        return ["id", "lon", "lat", "timestamp", "precip_rate", "precip_prob", "precip_type"]
