import json

from metrics.parse.forecast.foreca import ForecaParser
from metrics.utils.precipitation import PrecipitationType


def test_the_parse_impl_equals_the_raw_parse():
    data = json.dumps({"position": {"lat": 52.0, "lon": 21.0},
                       "payload": {"forecast": [{"time": "2024-01-01T00:00:00+00:00", "precipRate": 1.5,
                                                 "precipProb": 30, "precipType": "rain"}]}}).encode()
    parser = ForecaParser()

    rows = parser._parse_impl(1, "EPWA.json", data)

    assert rows == parser.parse_raw(1, "EPWA.json", data)
    assert rows == [("EPWA", 21.0, 52.0, 1704067200, 1.5, 0.3, PrecipitationType.RAIN.value)]
