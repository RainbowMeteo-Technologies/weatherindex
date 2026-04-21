import json

from metrics.parse.forecast.flashnet import FlashNetParser
from metrics.utils.precipitation import PrecipitationType


def _mock_flashnet_response(lon: float = 2.35, lat: float = 48.85, forecasts=None):
    if forecasts is None:
        forecasts = [
            {
                "valid_time": "2026-04-21T15:00:00Z",
                "valid_time_epoch": 1776805200,
                "offset_minutes": 10,
                "precip_rate_mmh": 0.0,
                "precip_type": "none",
                "precip_prob": 0.0
            },
            {
                "valid_time": "2026-04-21T15:10:00Z",
                "valid_time_epoch": 1776805800,
                "offset_minutes": 20,
                "precip_rate_mmh": 1.5,
                "precip_type": "rain",
                "precip_prob": 1.0
            }
        ]
    return {
        "location": {"lon": lon, "lat": lat},
        "issuance_time": "2026-04-21T14:50:00Z",
        "forecasts": forecasts,
        "coverage": "ok"
    }


class TestFlashNetParser:
    def test_parse_smoke(self):
        """Test basic parsing with rain and none entries."""
        data = _mock_flashnet_response()
        data_bytes = json.dumps(data).encode("utf-8")

        parser = FlashNetParser()
        rows = parser._parse_impl(timestamp=0,
                                  file_name="LFPG.json",
                                  data=data_bytes)

        assert len(rows) == 2

        # columns: id, lon, lat, timestamp, precip_rate, precip_prob, precip_type
        id_, lon, lat, ts, rate, prob, ptype = rows[0]
        assert id_ == "LFPG"
        assert lon == 2.35
        assert lat == 48.85
        assert ts == 1776805200
        assert rate == 0.0
        assert prob == 0.0
        assert ptype == PrecipitationType.UNKNOWN.value

        _, _, _, ts2, rate2, prob2, ptype2 = rows[1]
        assert ts2 == 1776805800
        assert rate2 == 1.5
        assert prob2 == 1.0
        assert ptype2 == PrecipitationType.RAIN.value

    def test_parse_empty_forecasts(self):
        """Test parsing when no forecasts are available (e.g. out_of_bounds)."""
        data = _mock_flashnet_response(forecasts=[])
        data_bytes = json.dumps(data).encode("utf-8")

        parser = FlashNetParser()
        rows = parser._parse_impl(timestamp=0,
                                  file_name="OUTOFBOUNDS.json",
                                  data=data_bytes)

        assert len(rows) == 0

    def test_parse_snow_type(self):
        """Test that snow precip_type is correctly mapped."""
        data = _mock_flashnet_response(forecasts=[
            {
                "valid_time": "2026-04-21T15:00:00Z",
                "valid_time_epoch": 1776805200,
                "offset_minutes": 10,
                "precip_rate_mmh": 2.0,
                "precip_type": "snow",
                "precip_prob": 1.0
            }
        ])
        data_bytes = json.dumps(data).encode("utf-8")

        parser = FlashNetParser()
        rows = parser._parse_impl(timestamp=0,
                                  file_name="SNOW.json",
                                  data=data_bytes)

        assert len(rows) == 1
        _, _, _, _, rate, _, ptype = rows[0]
        assert rate == 2.0
        assert ptype == PrecipitationType.SNOW.value

    def test_parse_mix_type(self):
        """Test that mix precip_type is correctly mapped."""
        data = _mock_flashnet_response(forecasts=[
            {
                "valid_time": "2026-04-21T15:00:00Z",
                "valid_time_epoch": 1776805200,
                "offset_minutes": 10,
                "precip_rate_mmh": 0.5,
                "precip_type": "mix",
                "precip_prob": 0.8
            }
        ])
        data_bytes = json.dumps(data).encode("utf-8")

        parser = FlashNetParser()
        rows = parser._parse_impl(timestamp=0,
                                  file_name="MIX.json",
                                  data=data_bytes)

        assert len(rows) == 1
        _, _, _, _, rate, prob, ptype = rows[0]
        assert rate == 0.5
        assert prob == 0.8
        assert ptype == PrecipitationType.MIX.value

    def test_should_parse_json(self):
        """Test that only .json files are parsed."""
        parser = FlashNetParser()
        assert parser._should_parse_file_extension(".json") is True
        assert parser._should_parse_file_extension(".csv") is False
        assert parser._should_parse_file_extension(".xml") is False

    def test_get_columns(self):
        """Test that the parser returns the expected canonical columns."""
        parser = FlashNetParser()
        columns = parser._get_columns()
        assert columns == ["id", "lon", "lat", "timestamp",
                          "precip_rate", "precip_prob", "precip_type"]
