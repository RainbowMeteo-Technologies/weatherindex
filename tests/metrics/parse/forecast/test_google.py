import pytest
import json

from metrics.parse.forecast.google import GoogleParser, _parse_time
from metrics.utils.precipitation import PrecipitationType

SNAPSHOT = _parse_time("2026-05-11T12:10:00Z")


def _segment(start: str, end: str, precip_type: str, probability: int,
             qpf: float = None, snowfall: float = None) -> dict:
    segment = {
        "timeFrame": {"startTime": start, "endTime": end},
        "type": precip_type,
        "probability": probability,
    }
    if qpf is not None:
        segment["qpf"] = {"quantity": qpf, "unit": "MILLIMETERS"}
    if snowfall is not None:
        segment["snowfallAmount"] = {"quantity": snowfall, "unit": "MILLIMETERS"}
    return segment


def _payload(segments: list) -> dict:
    return {
        "overallPredictionTimeframe": {"startTime": "2026-05-11T12:10:00Z", "endTime": "2026-05-11T13:10:00Z"},
        "timeZone": {"id": "Europe/London"},
        "segments": segments,
    }


@pytest.mark.parametrize("payload, expected_rows", [
    # rate from segment length: 0.1333 mm over 2 minutes
    (
        _payload([_segment("2026-05-11T12:10:00Z", "2026-05-11T12:12:00Z", "RAIN", 21, qpf=0.1333)]),
        [("TEST_ID", 1.0, 2.0, _parse_time("2026-05-11T12:10:00Z"),
          pytest.approx(0.1333 / 120 * 3600), 0.21, PrecipitationType.RAIN.value)]
    ),
    # longer segment, fractional seconds
    (
        _payload([_segment("2026-05-11T12:10:00.123Z", "2026-05-11T12:40:00.123Z", "RAIN", 50, qpf=1.5)]),
        [("TEST_ID", 1.0, 2.0, _parse_time("2026-05-11T12:10:00Z"),
          pytest.approx(3.0), 0.5, PrecipitationType.RAIN.value)]
    ),
    # snow: max of qpf and snowfallAmount
    (
        _payload([_segment("2026-05-11T12:10:00Z", "2026-05-11T12:20:00Z", "SNOW", 70, qpf=0.2, snowfall=1.0)]),
        [("TEST_ID", 1.0, 2.0, _parse_time("2026-05-11T12:10:00Z"),
          pytest.approx(6.0), 0.7, PrecipitationType.SNOW.value)]
    ),
    # hail is mapped to rain
    (
        _payload([_segment("2026-05-11T12:10:00Z", "2026-05-11T12:20:00Z", "HAIL", 100, qpf=1.0)]),
        [("TEST_ID", 1.0, 2.0, _parse_time("2026-05-11T12:10:00Z"),
          pytest.approx(6.0), 1.0, PrecipitationType.RAIN.value)]
    ),
    # none / unspecified -> unknown, missing amounts -> 0
    (
        _payload([_segment("2026-05-11T12:10:00Z", "2026-05-11T12:40:00Z", "NONE", 0),
                  _segment("2026-05-11T12:40:00Z", "2026-05-11T13:10:00Z",
                           "DOMINANT_PRECIPITATION_TYPE_UNSPECIFIED", 5)]),
        [("TEST_ID", 1.0, 2.0, _parse_time("2026-05-11T12:10:00Z"), 0.0, 0.0, PrecipitationType.UNKNOWN.value),
         ("TEST_ID", 1.0, 2.0, _parse_time("2026-05-11T12:40:00Z"), 0.0, 0.05, PrecipitationType.UNKNOWN.value)]
    ),
    # 1 hour cutoff: segment starting exactly at +60 min kept, later dropped
    (
        _payload([_segment("2026-05-11T13:10:00Z", "2026-05-11T13:20:00Z", "RAIN", 30, qpf=0.5),
                  _segment("2026-05-11T13:10:01Z", "2026-05-11T13:20:00Z", "RAIN", 30, qpf=0.5),
                  _segment("2026-05-11T14:00:00Z", "2026-05-11T14:10:00Z", "RAIN", 30, qpf=0.5)]),
        [("TEST_ID", 1.0, 2.0, _parse_time("2026-05-11T13:10:00Z"),
          pytest.approx(3.0), 0.3, PrecipitationType.RAIN.value)]
    ),
    # zero-length segment is skipped
    (
        _payload([_segment("2026-05-11T12:10:00Z", "2026-05-11T12:10:00Z", "RAIN", 30, qpf=0.5)]),
        []
    ),
    # no segments
    (
        {"overallPredictionTimeframe": {}},
        []
    ),
])
def test_google(payload, expected_rows):
    json_data = {
        "position": {
            "lon": 1.0,
            "lat": 2.0
        },
        "payload": payload
    }

    json_str = json.dumps(json_data)
    parser = GoogleParser()
    rows = parser._parse_impl(SNAPSHOT, "TEST_ID.json", bytes(json_str, 'utf-8'))

    assert rows == expected_rows


def test_google_missing_position():
    json_data = {
        "payload": _payload([_segment("2026-05-11T12:10:00Z", "2026-05-11T12:20:00Z", "RAIN", 50, qpf=1.0)])
    }

    parser = GoogleParser()
    rows = parser._parse_impl(SNAPSHOT, "TEST_ID.json", bytes(json.dumps(json_data), 'utf-8'))

    assert rows == []
