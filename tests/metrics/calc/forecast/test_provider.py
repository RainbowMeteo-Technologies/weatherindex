import pandas
import pytest
import typing

from metrics.calc.forecast.provider import ForecastProvider


def _create_sensors_table(data: typing.List[any]) -> pandas.DataFrame:
    return pandas.DataFrame(columns=["id", "lon", "lat"], data=data)


def _create_precip_table(data: typing.List[any]) -> pandas.DataFrame:
    return pandas.DataFrame(columns=["id", "precip_rate", "precip_type", "forecast_time"], data=data)


class TestForecastProvider:

    @pytest.mark.parametrize("sensors_table, data, expected_data", [
        (
            # sensors_table
            _create_sensors_table([
                ("sensor_1", 53, 23),
                ("sensor_2", 53, 24)
            ]),
            # data
            _create_precip_table([
                ("sensor_1", 5, 0, 1200),
                ("sensor_3", 10, 1, 600),
            ]),
            # expected_data
            _create_precip_table([
                ("sensor_1", 5, 0, 1200),
            ])
        )
    ])
    def test_filter_by_sensors(self,
                               sensors_table: pandas.DataFrame,
                               data: pandas.DataFrame,
                               expected_data: pandas.DataFrame):

        provider = ForecastProvider()

        result = provider._filter_by_sensors(sensors_table=sensors_table,
                                             data=data)

        pandas.testing.assert_frame_equal(result.reset_index(drop=True),
                                          expected_data.reset_index(drop=True))
