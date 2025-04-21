import pytest

from metrics.parse.forecast.weather_kit import _condition_to_precip_type, _parse_time, WeatherKitParser, OutputRowType
from metrics.utils.precipitation import PrecipitationType


class TestWeatherKit:

    @pytest.mark.parametrize("forecast_json, expected_rows", [
        # Senario:
        # - rain become a snow
        (
            # forecast_json
            {
                "metadata": {
                    "latitude": 51.458,
                    "longitude": -3.283,
                },
                "summary": [
                    {
                        "startTime": "2023-11-05T01:00:00Z",
                        "endTime": "2023-11-05T01:01:00Z",
                        "condition": "rain",
                    },
                    {
                        "startTime": "2023-11-05T01:01:00Z",
                        "condition": "snow"
                    }
                ],
                "minutes": [
                    {
                        "startTime": "2023-11-05T01:00:00Z",
                        "precipitationChance": 0.73,
                        "precipitationIntensity": 0.09
                    },
                    {
                        "startTime": "2023-11-05T01:01:00Z",
                        "precipitationChance": 0.28,
                        "precipitationIntensity": 0.09
                    },
                    {
                        "startTime": "2023-11-05T01:02:00Z",
                        "precipitationChance": 0.7,
                        "precipitationIntensity": 0.43
                    }
                ]
            },
            # expected_rows
            [
                # "id", "lon", "lat", "timestamp", "precip_rate", "precip_prob", "precip_type"
                ("test_sensor", -3.283, 51.458, 1699146000, 0.09, 0.73, PrecipitationType.RAIN),
                ("test_sensor", -3.283, 51.458, 1699146060, 0.0, 0.28, PrecipitationType.SNOW),
                ("test_sensor", -3.283, 51.458, 1699146120, 0.43, 0.7, PrecipitationType.SNOW),
            ]
        ),

        # Senario:
        # - precipitation starts with delay
        (
            # forecast_json
            {
                "metadata": {
                    "latitude": 51.458,
                    "longitude": -3.283,
                },
                "summary": [
                    {
                        "startTime": "2023-11-05T01:00:00Z",
                        "endTime": "2023-11-05T01:01:00Z",
                        "condition": "clear",
                    },
                    {
                        "startTime": "2023-11-05T01:01:00Z",
                        "endTime": "2023-11-05T01:02:00Z",
                        "condition": "snow"
                    },
                    {
                        "startTime": "2023-11-05T01:02:00Z",
                        "condition": "rain"
                    }
                ],
                "minutes": [
                    {
                        "startTime": "2023-11-05T01:00:00Z",
                        "precipitationChance": 0.0,
                        "precipitationIntensity": 0.00
                    },
                    {
                        "startTime": "2023-11-05T01:01:00Z",
                        "precipitationChance": 0.7,
                        "precipitationIntensity": 0.4
                    },
                    {
                        "startTime": "2023-11-05T01:02:00Z",
                        "precipitationChance": 0.7,
                        "precipitationIntensity": 0.43
                    }
                ]
            },
            # expected_rows
            [
                # "id", "lon", "lat", "timestamp", "precip_rate", "precip_prob", "precip_type"
                ("test_sensor", -3.283, 51.458, 1699146000, 0.0, 0.0, PrecipitationType.UNKNOWN),
                ("test_sensor", -3.283, 51.458, 1699146060, 0.4, 0.7, PrecipitationType.SNOW),
                ("test_sensor", -3.283, 51.458, 1699146120, 0.43, 0.7, PrecipitationType.RAIN),
            ]
        )
    ])
    def test_parse_next_hour(self, forecast_json: dict, expected_rows: OutputRowType):
        parser = WeatherKitParser()
        parsed_rows = parser._parse_next_hour("test_sensor", forecast=forecast_json)
        for row in parsed_rows:
            assert isinstance(row[-1], int)

        assert parsed_rows == expected_rows

    @pytest.mark.parametrize("condition, expected_type", [
        ("clear", PrecipitationType.UNKNOWN),
        ("precipitation", PrecipitationType.UNKNOWN),
        ("rain", PrecipitationType.RAIN),
        ("snow", PrecipitationType.SNOW),
        ("sleet", PrecipitationType.SNOW),
        ("hail", PrecipitationType.RAIN),
        ("mixed", PrecipitationType.RAIN)
    ])
    def test_contdition_to_precip_type(self, condition: str, expected_type: PrecipitationType):
        assert _condition_to_precip_type(condition=condition) == expected_type

    @pytest.mark.parametrize("time_str, expected_timestamp", [
        ("2023-11-05T01:00:00Z", 1699146000)
    ])
    def test_parse_time(self, time_str: str, expected_timestamp: int):
        parsed_timestamp = _parse_time(time_str=time_str)

        assert isinstance(parsed_timestamp, int)
        assert parsed_timestamp == expected_timestamp
