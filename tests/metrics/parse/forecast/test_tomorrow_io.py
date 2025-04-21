import pytest
import json

from metrics.parse.forecast.tomorrow_io import TomorrowIoParser, _parse_time
from metrics.utils.precipitation import PrecipitationType


@pytest.mark.parametrize("payload, expected_rows", [
    # 1hour forecast
    (
        {
            "timelines": {
                "minutely": [
                    {
                        "time": "2024-10-01T07:51:00Z",
                        "values": {
                            "cloudBase": None,
                            "cloudCeiling": None,
                            "cloudCover": 5,
                            "dewPoint": 13.88,
                            "freezingRainIntensity": 0,
                            "humidity": 89,
                            "precipitationProbability": 80,
                            "pressureSurfaceLevel": 1002.85,
                            "rainIntensity": 0.1,
                            "sleetIntensity": 0,
                            "snowIntensity": 0,
                            "temperature": 15.69,
                            "temperatureApparent": 15.69,
                            "uvHealthConcern": 0,
                            "uvIndex": 0,
                            "visibility": 14.46,
                            "weatherCode": 1000,
                            "windDirection": 94,
                            "windGust": 5.38,
                            "windSpeed": 4.5
                        }
                    }
                ]
            }
        },
        [("TEST_ID", 1.0, 1.0, _parse_time("2024-10-01T07:51:00Z"), 0.1, 0.8, PrecipitationType.RAIN.value)]
    ),

    # 6hours forecast
    (
        {
            "data": {
                "timelines": [
                    {
                        "timestep": "1m",
                        "endTime": "2024-10-01T14:52:00Z",
                        "startTime": "2024-10-01T08:52:00Z",
                        "intervals": [
                            {
                                "startTime": "2024-10-01T05:55:00Z",
                                "values": {
                                    "precipitationProbability": 90,
                                    "rainIntensity": 6.54,
                                    "sleetIntensity": 0,
                                    "snowIntensity": 0,
                                    "temperature": 20.35
                                }
                            }
                        ]
                    }
                ]
            }
        },
        [("TEST_ID", 1.0, 1.0, _parse_time("2024-10-01T05:55:00Z"), 6.54, 0.9, PrecipitationType.RAIN.value)]
    )
])
def test_tomorrowio(payload, expected_rows):
    json_data = {
        "position": {
            "lon": 1.0,
            "lat": 1.0
        },
        "payload": payload
    }

    json_str = json.dumps(json_data)
    parser = TomorrowIoParser()
    rows = parser._parse_impl(0, "TEST_ID.json", bytes(json_str, 'utf-8'))

    assert rows == expected_rows
