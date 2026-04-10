import json
import os
import pandas as pd
import typing

from dateutil.parser import isoparse
from metrics.parse.base_parser import BaseParser

from rich.console import Console
from metrics.utils.precipitation import PrecipitationType


console = Console()


def _parse_time(time_str: str) -> int:
    return int(isoparse(time_str).timestamp())


def _parse_precip_type(precip_type: str) -> PrecipitationType:
    if precip_type == "rain":
        return PrecipitationType.RAIN
    elif precip_type == "snow":
        return PrecipitationType.SNOW
    elif precip_type == "precip":
        return PrecipitationType.MIX

    raise ValueError(f"Unknown precipitation type: {precip_type}")


class WeatherCompanyParser(BaseParser):
    def _parse_impl(self, timestamp: int, file_name: str, data: bytes) -> typing.List[typing.List[any]]:
        """See :func:`~metrics.base_parser.BaseParser._parse_impl`"""
        rows = []
        data_json = json.loads(data)
        sensor_id = os.path.basename(file_name).replace(".json", "")

        lat = data_json["position"]["lat"]
        lon = data_json["position"]["lon"]

        local_times_str_list = data_json["payload"]["validTimeLocal"]
        precip_types = data_json["payload"]["precipType"]
        precip_rates = data_json["payload"]["precipRate"]
        snow_rates = data_json["payload"]["snowRate"]
        precip_probs = data_json["payload"]["precipChance"]

        for local_time_str, precip_type, precip_rate, snow_rate, precip_prob in zip(local_times_str_list,
                                                                                    precip_types,
                                                                                    precip_rates,
                                                                                    snow_rates,
                                                                                    precip_probs):
            timestamp = int(_parse_time(local_time_str))
            precip_type = _parse_precip_type(precip_type)
            snow_rate = snow_rate * 10.0
            precip_rate = precip_rate
            precip_prob = precip_prob / 100.0

            if precip_prob == 0.0:
                precip_type = PrecipitationType.UNKNOWN

            if precip_type == PrecipitationType.MIX:
                precip_rate = max(precip_rate, snow_rate)
            elif precip_type == PrecipitationType.SNOW:
                precip_rate = snow_rate

            rows.append((sensor_id, lon, lat, timestamp, precip_rate, precip_prob, precip_type))

        df = pd.DataFrame(rows, columns=self._get_columns())

        # console.log(f"Orig: {df}")

        df["time"] = pd.to_datetime(df["timestamp"], unit="s")

        df = df.set_index("time")
        prate = df["precip_rate"].resample("5min").interpolate("time")
        timestamp = df["timestamp"].resample("5min").interpolate("time").astype(int)

        df = df.resample("5min").ffill()
        df["precip_rate"] = prate
        df["timestamp"] = timestamp

        df = df.reset_index().drop(columns=["time"])[self._get_columns()]

        # console.log(f"Interpolated: {df}")

        return list(df.itertuples(index=False, name=None))

    def _should_parse_file_extension(self, file_extension: str) -> bool:
        """See :func:`~metrics.base_parser.BaseParser._should_parse_file_extension`"""
        return file_extension == ".json"

    def _get_columns(self) -> typing.List[str]:
        """See :func:`~metrics.base_parser.BaseParser._get_columns`"""
        return ["id", "lon", "lat", "timestamp", "precip_rate", "precip_prob", "precip_type"]
