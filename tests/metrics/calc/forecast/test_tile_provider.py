import pandas
import pytest
import typing

from metrics.utils.coords import Coordinate
from metrics.utils.precipitation import PrecipitationType

from metrics.calc.forecast.tile_provider import TileProvider
from metrics.io.tile_loader import BaseTileLoader
from metrics.io.tile_reader import PrecipValue

from unittest.mock import Mock


def _create_sensors_table(data: typing.List[any]) -> pandas.DataFrame:
    return pandas.DataFrame(columns=["id", "lon", "lat"], data=data)


def _create_precip_table(data: typing.List[any]) -> pandas.DataFrame:
    return pandas.DataFrame(columns=["id", "precip_rate", "precip_type", "timestamp"], data=data)


class TestTileProvider:

    @pytest.mark.parametrize("snapshot_timestamp, sensors_table, mock_tile_data, expected_data", [
        # mock_tile_data - is a dict from input parameters
        # to output value for tile_reader.get_dbz_value_by_coords(lon, lat, offset)
        (
            # snapshot_timestamp
            7200,
            # sensors_table
            _create_sensors_table([
                ("sensor_1", 23.0, 51.0),
                ("sensor_2", 23.0, 52.0)
            ]),
            # mock_data
            {
                (23.0, 51.0, 0): PrecipValue(dbz=10, precip_type=PrecipitationType.RAIN),
                (23.0, 52.0, 600): PrecipValue(dbz=11, precip_type=PrecipitationType.SNOW),
                (23.0, 53.0, 1200): None
            },
            # expected_data
            _create_precip_table([
                # TODO: fix precip_rate to correct values
                ("sensor_1", 0.153765, PrecipitationType.RAIN.value, 7200),
                ("sensor_2", 0.250891, PrecipitationType.SNOW.value, 7800)
            ])
        ),
    ])
    def test_load(self,
                  snapshot_timestamp: int,
                  sensors_table: pandas.DataFrame,
                  mock_tile_data: typing.Dict[any, PrecipValue],
                  expected_data: pandas.DataFrame):

        provider = TileProvider(snapshots_path="test_rainbow_dir",
                                snapshot_timestamp=snapshot_timestamp,
                                tile_loader_class=BaseTileLoader,
                                max_forecast_time=7200,
                                forecast_step=600)

        def mock_get_dbz_value_by_coords(coords: Coordinate, offset: int) -> PrecipValue:
            return mock_tile_data.get((coords.lon, coords.lat, offset * 60), None)

        provider._tile_reader = Mock()
        provider._tile_reader.get_dbz_value_by_coords = mock_get_dbz_value_by_coords

        result = provider.load(sensors_table=sensors_table)

        # check None separately
        pandas.testing.assert_frame_equal(result.reset_index(drop=True),
                                          expected_data.reset_index(drop=True),
                                          check_like=True)

    @pytest.mark.parametrize("precip_type, dbz, expected_precipitation_rate", [
        (PrecipitationType.RAIN, 10, 0.153765),
        (PrecipitationType.SNOW, 10, 0.223606),
        (PrecipitationType.MIX, 10, 0.223606),
    ])
    def test_dbz_to_precipitation_rate(self,
                                       precip_type: PrecipitationType,
                                       dbz: float,
                                       expected_precipitation_rate: float):
        precip_rate = TileProvider.dbz_to_precipitation_rate(dbz=dbz, precip_type=precip_type)
        approx_precip_rate = pytest.approx(precip_rate, abs=1e-6)
        assert approx_precip_rate == expected_precipitation_rate
