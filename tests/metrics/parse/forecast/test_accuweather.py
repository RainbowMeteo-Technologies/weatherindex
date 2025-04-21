

import json
from typing import List, Tuple
from metrics.parse.forecast.accuweather import AccuWeatherParser
from metrics.utils.precipitation import PrecipitationType


def _mock_accuweather_response(lon: float = 14.75,
                               lat: float = 56.196,
                               forecasts: List[Tuple[int, int, PrecipitationType]] = []):
    summaries = []
    for start, end, precip_type in forecasts:
        summaries.append({"StartMinute": start,
                          "EndMinute": end,
                          "Type": precip_type.name,
                          "CountMinute": 120,
                          "TypeId": 42,
                          "MinuteText": "Not relevant"})
    return {
        "position": {
            "lon": lon,
            "lat": lat
        },
        "payload": {
            "Summaries": summaries
        }
    }


class TestAccuWeatherParser:
    def test_parse_smoke(self):
        data = _mock_accuweather_response(forecasts=[(0, 10, PrecipitationType.SNOW)])
        data_bytes = json.dumps(data).encode("utf-8")

        parser = AccuWeatherParser()
        rows = parser._parse_impl(timestamp=0,
                                  file_name="sensor.json",
                                  data=data_bytes)

        assert len(rows) == 11
        assert all(r[-1] == PrecipitationType.SNOW.value for r in rows)
