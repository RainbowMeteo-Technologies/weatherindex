import json

from metrics.parse.forecast.weather_company import WeatherCompanyParser
from metrics.utils.precipitation import PrecipitationType


def _file(precip_type, precip_rate, snow_rate, precip_chance):
    return json.dumps({
        "position": {"lat": 52.0, "lon": 21.0},
        "payload": {"validTimeLocal": ["2024-01-01T00:00:00+0000"], "precipType": [precip_type],
                    "precipRate": [precip_rate], "snowRate": [snow_rate], "precipChance": [precip_chance]},
    }).encode()


def test_the_rate_follows_the_type_even_at_zero_probability():
    [row] = WeatherCompanyParser().parse_raw(1, "EPWA.json", _file("snow", 1.0, 0.3, 0))

    assert row == ("EPWA", 21.0, 52.0, 1704067200, 3.0, 0.0, PrecipitationType.SNOW)


def test_a_zero_probability_sets_the_type_unknown_only_in_the_parse_impl():
    parser = WeatherCompanyParser()
    data = _file("rain", 1.0, 0.0, 0)

    [raw] = parser.parse_raw(1, "EPWA.json", data)
    [row] = parser._parse_impl(1, "EPWA.json", data)

    assert raw[-1] == PrecipitationType.RAIN
    assert row == ("EPWA", 21.0, 52.0, 1704067200, 1.0, 0.0, PrecipitationType.UNKNOWN)


def test_a_mixed_type_takes_the_larger_rate():
    [row] = WeatherCompanyParser()._parse_impl(1, "EPWA.json", _file("precip", 1.0, 0.3, 40))

    assert row == ("EPWA", 21.0, 52.0, 1704067200, 3.0, 0.4, PrecipitationType.MIX)
