
import pandas
import pytest
import typing

from metrics.calc.forecast.table_provider import TableProvider


def _create_sensors_table(data: typing.List[any]) -> pandas.DataFrame:
    return pandas.DataFrame(columns=["id", "lon", "lat"], data=data)


def _create_mock_table(data: typing.List[any]) -> pandas.DataFrame:
    return pandas.DataFrame(columns=["id", "precip_rate", "precip_type", "timestamp"], data=data)


def _create_precip_table(data: typing.List[any]) -> pandas.DataFrame:
    return pandas.DataFrame(columns=["id", "precip_rate", "precip_type", "timestamp"], data=data)


class TestAccuWeatherProvider:

    @pytest.mark.parametrize("snapshot_timestamp, sensors_table, mock_table, expected_data", [
        (
            # snapshot_timestamp
            7200,
            # sensors_table
            _create_sensors_table([
                ("sensor_1", 23, 52),
                ("sensor_2", 23, 53),
                ("sensor_3", 23, 54)]),
            # mock_data
            _create_mock_table([
                ("sensor_1", 0.0, 1, 7300),
                ("sensor_2", 3.0, 2, 8200),
                ("sensor_4", 4.0, 2, 8200),
            ]),
            # expected_data
            _create_precip_table([
                ("sensor_1", 0.0, 1, 7300),
                ("sensor_2", 3.0, 2, 8200)
            ])
        ),
        (
            # snapshot_timestamp
            7200,
            # sensors_table
            _create_sensors_table([
                ("sensor_1", 23, 52),
                ("sensor_2", 23, 53),
                ("sensor_3", 23, 54)]),
            # mock_data
            None,
            # expected_data
            None
        )
    ])
    def test_load(self,
                  snapshot_timestamp: int,
                  sensors_table: pandas.DataFrame,
                  mock_table: pandas.DataFrame,
                  expected_data: pandas.DataFrame):

        provider = TableProvider(tables_path="test_dir",
                                 snapshot_timestamp=snapshot_timestamp)

        provider._table = mock_table

        result = provider.load(sensors_table=sensors_table)

        # check None separately
        if expected_data is None:
            assert result == expected_data
        else:
            pandas.testing.assert_frame_equal(result.reset_index(drop=True),
                                              expected_data.reset_index(drop=True),
                                              check_like=True)
