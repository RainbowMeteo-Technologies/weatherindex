
import json
import os
import typing

from dataclasses import dataclass
from dateutil.parser import isoparse

from metrics.parse.base_parser import BaseParser
from rich.console import Console
from metrics.utils.precipitation import PrecipitationType


OutputRowType = typing.List[typing.Tuple[str, float, float, int, float, float, int]]

PROB_THRESHOLD = 0.7

console = Console()


def _parse_time(time_str: str) -> int:
    return int(isoparse(time_str).timestamp())


def _condition_to_precip_type(condition: str) -> PrecipitationType:
    if condition == "clear":
        return PrecipitationType.UNKNOWN
    elif condition == "precipitation":
        return PrecipitationType.UNKNOWN
    elif condition == "rain":
        return PrecipitationType.RAIN
    elif condition == "snow":
        return PrecipitationType.SNOW
    elif condition == "sleet":
        return PrecipitationType.SNOW
    elif condition == "hail":
        return PrecipitationType.RAIN
    elif condition == "mixed":
        return PrecipitationType.RAIN


@dataclass(frozen=True)
class SummaryRange:
    start_time: int  # timestamp
    end_time: typing.Optional[int]  # timestamp
    precip_type: PrecipitationType


class WeatherKitParser(BaseParser):

    def _parse_next_hour(self, sensor_id: str, forecast: dict) -> OutputRowType:
        """Parses `forecastNextHour` forecast from weather kit API response
        """
        result = []
        meta = forecast["metadata"]
        lon = float(meta["longitude"])
        lat = float(meta["latitude"])

        # parse summary ranges with types
        summaries: typing.List[SummaryRange] = []
        for summary in forecast["summary"]:
            start_time = _parse_time(summary["startTime"])
            end_time = None
            if "endTime" in summary:
                end_time = _parse_time(summary["endTime"])

            precip_type = _condition_to_precip_type(summary["condition"])
            summaries.append(SummaryRange(start_time=start_time,
                                          end_time=end_time,
                                          precip_type=precip_type))

        # sort summeries by start time
        summaries = sorted(summaries, key=lambda item: item.start_time)

        def _get_precip_type(timestamp: int) -> PrecipitationType:
            for item in summaries:
                if item.end_time is None or timestamp < item.end_time:
                    return item.precip_type

            return PrecipitationType.UNKNOWN

        for feature in forecast["minutes"]:
            timestamp = int(_parse_time(feature["startTime"]))
            precip_rate = float(feature["precipitationIntensity"])
            precip_prob = float(feature["precipitationChance"])
            precip_type = _get_precip_type(timestamp=timestamp)

            # override precip_rate and precip_prob based on precip type
            if precip_type == PrecipitationType.UNKNOWN:
                precip_prob = 0.0
                precip_rate = 0.0
            elif precip_prob < PROB_THRESHOLD:
                precip_rate = 0.0

            result.append((sensor_id, lon, lat, timestamp, precip_rate, precip_prob, precip_type.value))

        return result

    def _parse_impl(self, timestamp: int, file_name: str, data: bytes) -> typing.List[typing.List[any]]:
        """See :func:`~metrics.base_parser.BaseParser._parse_impl`"""
        rows = []
        try:
            data_json = json.loads(data)
            sensor_id = os.path.basename(file_name).replace(".json", "")

            if "forecastNextHour" in data_json:
                rows.extend(self._parse_next_hour(sensor_id=sensor_id,
                                                  forecast=data_json["forecastNextHour"]))
        except json.decoder.JSONDecodeError:
            console.log(f"json.decoder.JSONDecodeError on parsing {file_name} inside {timestamp}.zip")

        return rows

    def _should_parse_file_extension(self, file_extension: str) -> bool:
        """See :func:`~metrics.base_parser.BaseParser._should_parse_file_extension`"""
        return file_extension == ".json"

    def _get_columns(self) -> typing.List[str]:
        """See :func:`~metrics.base_parser.BaseParser._get_columns`"""
        return ["id", "lon", "lat", "timestamp", "precip_rate", "precip_prob", "precip_type"]
