import json
import os
import re

from dateutil.parser import isoparse
from metrics.parse.base_parser import BaseParser
from metrics.utils.precipitation import PrecipitationType
from rich.console import Console
from typing import Any
from typing_extensions import override


console = Console()


def _parse_15min_forecast(sensor_id: str, data_json: dict) -> list[list[Any]]:
    # https://www.ibm.com/docs/en/environmental-intel-suite?topic=apis-short-range-forecast-15-minute

    rows = []

    lat = data_json["position"]["lat"]
    lon = data_json["position"]["lon"]

    local_times_str_list = data_json["payload"]["validTimeLocal"]
    precip_types = data_json["payload"]["precipType"]
    precip_rates = data_json["payload"]["precipRate"]
    snow_rates = data_json["payload"]["snowRate"]
    precip_probs = data_json["payload"]["precipChance"]

    def _parse_precip_type(precip_type: str) -> PrecipitationType:
        if precip_type == "rain":
            return PrecipitationType.RAIN
        elif precip_type == "snow":
            return PrecipitationType.SNOW
        elif precip_type == "precip":
            return PrecipitationType.MIX

        raise ValueError(f"Unknown precipitation type: {precip_type}")

    def _parse_time(time_str: str) -> int:
        return int(isoparse(time_str).timestamp())

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

        rows.append([sensor_id, lon, lat, timestamp, precip_rate, precip_prob, precip_type, None])

    return rows


def _parse_precipitation_forecast(sensor_id: str, data_json: dict) -> list[list[Any]]:
    # https://www.ibm.com/docs/en/environmental-intel-suite?topic=apis-short-range-forecast-precipitation-forecast

    payload = data_json["payload"]
    meta = payload["metadata"]

    if (status_code := meta["status_code"]) != 200:
        console.log(f"Invalid status code from TWC API: {status_code}")
        return []

    lat = meta["latitude"]
    lon = meta["longitude"]

    transaction_id = meta["transaction_id"]
    if (match := re.match(r"^(?P<timestamp>\d{13}):.+$", transaction_id)) is None:
        console.log(f"Failed to extract forecast timestamp from transaction ID: {transaction_id}")
        return []

    # TODO: align base_timestamp to nearest value divideable by 600? just to prevent aligning values < 20sec to 600sec
    base_timestamp = int(match.group("timestamp")) // 1e+3  # conversion from milliseconds

    base_timestamp = int(round(base_timestamp / 600) * 600)

    rows = []

    FORECAST_STEP = 600  # 10 minutes

    # maps TWC's event type to RMT's one
    precip_code_mapping: dict[int, PrecipitationType] = {
        0: PrecipitationType.RAIN,  # none
        1: PrecipitationType.RAIN,  # rain
        2: PrecipitationType.SNOW,  # snow
        3: PrecipitationType.MIX,  # mix
        4: PrecipitationType.RAIN,  # thunder
    }

    for event in payload["forecasts"]:

        if (event_class := event["class"]) != "fod_short_range_precipitation":
            console.log(f"Unknown event class: {event_class}, skipping")
            continue

        event_start = event["event_start"]
        event_end = event["event_end"]
        event_length = (event_end - event_start) / 3600  # hours

        precip_type = precip_code_mapping[event["event_type"]]
        rain_rate = event["qpf"] / event_length
        snow_rate = event["snow_qpf"] / event_length

        precip_rate = rain_rate
        if precip_type == PrecipitationType.SNOW:
            precip_rate = snow_rate
        elif precip_rate == PrecipitationType.MIX:
            precip_rate = max(rain_rate, snow_rate)

        aligned_timestamp = event_start
        if (aligned_timestamp - base_timestamp) % FORECAST_STEP != 0:
            aligned_timestamp += FORECAST_STEP - ((aligned_timestamp - base_timestamp) % FORECAST_STEP)

        while aligned_timestamp < event_end:

            forecast_time = aligned_timestamp - base_timestamp

            rows.append([sensor_id,
                         lon,
                         lat,
                         int(aligned_timestamp),
                         precip_rate,
                         1.0,  # precip_prob
                         precip_type,
                         int(forecast_time)
                         ])

            aligned_timestamp += FORECAST_STEP

    return rows


class WeatherCompanyParser(BaseParser):

    @override
    def _parse_impl(self, timestamp: int, file_name: str, data: bytes) -> list[list[Any]]:
        """See :func:`~metrics.base_parser.BaseParser._parse_impl`"""
        data_json = json.loads(data)

        sensor_id = os.path.basename(file_name).replace(".json", "")

        product_id = data_json.get("product_name", "forecast-15-minute")

        if product_id == "forecast-15-minute":
            return _parse_15min_forecast(sensor_id, data_json)
        elif product_id == "forecast-precipitation":
            return _parse_precipitation_forecast(sensor_id, data_json)
        else:
            console.log(f"Unknown product id: {product_id}")
            return []

    @override
    def _should_parse_file_extension(self, file_extension: str) -> bool:
        """See :func:`~metrics.base_parser.BaseParser._should_parse_file_extension`"""
        return file_extension == ".json"

    @override
    def _get_columns(self) -> list[str]:
        """See :func:`~metrics.base_parser.BaseParser._get_columns`"""
        return ["id", "lon", "lat", "timestamp", "precip_rate", "precip_prob", "precip_type", "forecast_time"]
