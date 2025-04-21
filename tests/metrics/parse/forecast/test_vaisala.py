import pytest
import json

from metrics.parse.forecast.vaisala import VaisalaParser
from metrics.utils.precipitation import PrecipitationType


@pytest.mark.parametrize("payload, expected_rows", [
    # 1hour forecast without probability field, only rain
    (
        {
            "success": True,
            "error": None,
            "response": [
                {
                    "loc": {
                        "lat": 50.703,
                        "long": -119.291
                    },
                    "place": {
                        "name": "salmon arm",
                        "state": "bc",
                        "country": "ca"
                    },
                    "periods": [
                        {
                            "timestamp": 1727760600,
                            "dateTimeISO": "2024-09-30T22:30:00-07:00",
                            "precipMM": 0,
                            "precipIN": 0.000099999999999989,
                            "precipRateMM": 0.18,
                            "precipRateIN": 0.0071000000000001,
                            "snowCM": 0,
                            "snowIN": 0,
                            "snowRateCM": 0,
                            "snowRateIN": 0,
                            "weatherPrimary": "Rain Showers",
                            "weatherPrimaryCoded": ":VL:RW",
                            "icon": "showersn.png",
                            "isDay": False
                        }
                    ],
                    "profile": {
                        "tz": "America/Vancouver",
                        "tzname": "PDT",
                        "tzoffset": -25200,
                        "isDST": True,
                        "elevM": 427,
                        "elevFT": 1401
                    }
                }
            ]
        },
        [("TEST_ID", 1.0, 1.0, 1727760600, 0.18, 0.0, PrecipitationType.RAIN.value)]
    ),

    # 1hour forecast without probability field, only snow
    (
        {
            "success": True,
            "error": None,
            "response": [
                {
                    "loc": {
                        "lat": 50.703,
                        "long": -119.291
                    },
                    "place": {
                        "name": "salmon arm",
                        "state": "bc",
                        "country": "ca"
                    },
                    "periods": [
                        {
                            "timestamp": 1727760600,
                            "dateTimeISO": "2024-09-30T22:30:00-07:00",
                            "precipMM": 0,
                            "precipIN": 0.000099999999999989,
                            "precipRateMM": 0,
                            "precipRateIN": 0.0071000000000001,
                            "snowCM": 0,
                            "snowIN": 0,
                            "snowRateCM": 1.8,
                            "snowRateIN": 0.07086614173228346,
                            "weatherPrimary": "Rain Showers",
                            "weatherPrimaryCoded": ":VL:RW",
                            "icon": "showersn.png",
                            "isDay": False
                        }
                    ],
                    "profile": {
                        "tz": "America/Vancouver",
                        "tzname": "PDT",
                        "tzoffset": -25200,
                        "isDST": True,
                        "elevM": 427,
                        "elevFT": 1401
                    }
                }
            ]
        },
        [("TEST_ID", 1.0, 1.0, 1727760600, 0.18, 0.0, PrecipitationType.SNOW.value)]
    ),

    # 1hour forecast without probability field, mix
    (
        {
            "success": True,
            "error": None,
            "response": [
                {
                    "loc": {
                        "lat": 50.703,
                        "long": -119.291
                    },
                    "place": {
                        "name": "salmon arm",
                        "state": "bc",
                        "country": "ca"
                    },
                    "periods": [
                        {
                            "timestamp": 1727760600,
                            "dateTimeISO": "2024-09-30T22:30:00-07:00",
                            "precipMM": 0,
                            "precipIN": 0.000099999999999989,
                            "precipRateMM": 0.18,
                            "precipRateIN": 0.0071000000000001,
                            "snowCM": 0,
                            "snowIN": 0,
                            "snowRateCM": 1.9,
                            "snowRateIN": 0.07480314960629921,
                            "weatherPrimary": "Rain Showers",
                            "weatherPrimaryCoded": ":VL:RW",
                            "icon": "showersn.png",
                            "isDay": False
                        }
                    ],
                    "profile": {
                        "tz": "America/Vancouver",
                        "tzname": "PDT",
                        "tzoffset": -25200,
                        "isDST": True,
                        "elevM": 427,
                        "elevFT": 1401
                    }
                }
            ]
        },
        [("TEST_ID", 1.0, 1.0, 1727760600, 0.19, 0.0, PrecipitationType.MIX.value)]
    ),


    # 1hour forecast with probability field
    (
        {
            "success": True,
            "error": None,
            "response": [
                {
                    "loc": {
                        "lat": 50.703,
                        "long": -119.291
                    },
                    "place": {
                        "name": "salmon arm",
                        "state": "bc",
                        "country": "ca"
                    },
                    "periods": [
                        {
                            "timestamp": 1727760600,
                            "dateTimeISO": "2024-09-30T22:30:00-07:00",
                            "precipMM": 0,
                            "precipIN": 0.000099999999999989,
                            "precipRateMM": 0.18,
                            "precipRateIN": 0.0071000000000001,
                            "snowCM": 0,
                            "snowIN": 0,
                            "snowRateCM": 0,
                            "snowRateIN": 0,
                            "weatherPrimary": "Rain Showers",
                            "weatherPrimaryCoded": ":VL:RW",
                            "icon": "showersn.png",
                            "isDay": False,
                            "pop": 0.75
                        }
                    ],
                    "profile": {
                        "tz": "America/Vancouver",
                        "tzname": "PDT",
                        "tzoffset": -25200,
                        "isDST": True,
                        "elevM": 427,
                        "elevFT": 1401
                    }
                }
            ]
        },
        [("TEST_ID", 1.0, 1.0, 1727760600, 0.18, 0.75, PrecipitationType.RAIN.value)]
    )
])
def test_vaisala(payload, expected_rows):
    json_data = {
        "position": {
            "lon": 1.0,
            "lat": 1.0
        },
        "payload": payload
    }

    json_str = json.dumps(json_data)
    parser = VaisalaParser()
    rows = parser._parse_impl(0, "TEST_ID.json", bytes(json_str, 'utf-8'))

    assert rows == expected_rows
