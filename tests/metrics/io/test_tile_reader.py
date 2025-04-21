import numpy as np
import mercantile
import pytest
import typing

from metrics.io.tile_reader import TileReader, PrecipValue
from metrics.utils.coords import Coordinate, PixelCoordinate
from metrics.utils.precipitation import PrecipitationType, PrecipitationData
from unittest.mock import MagicMock


class TestTileReader:

    @pytest.mark.parametrize("coords, expected_result", [
        (
            Coordinate(lon=-87.65, lat=41.85),
            (mercantile.Tile(32, 47, 7), PixelCoordinate(x=213, y=150, zoom=7))
        ),
        (
            Coordinate(lon=20.321, lat=-5.302),
            (mercantile.Tile(71, 65, 7), PixelCoordinate(x=57, y=226, zoom=7))
        )
    ])
    def test_calculate_pixel_coordinates(self,
                                         coords: Coordinate,
                                         expected_result: typing.Tuple[mercantile.Tile, PixelCoordinate]):

        reader = TileReader(None)
        assert reader._calculate_pixel_coordinates(coords=coords) == expected_result

    @pytest.mark.parametrize("precip_value, expected_rain", [
        (PrecipValue(0.0, PrecipitationType.SNOW), False),
        (PrecipValue(0.0, PrecipitationType.RAIN), True),
    ])
    def test_precip_value(self, precip_value: PrecipValue, expected_rain: bool):
        assert precip_value.is_rain() == expected_rain

    @pytest.mark.parametrize("reflectivity, expected_dbz", [
        (np.zeros((1, 1), dtype=np.float32), 0),
        (np.ones((1, 1), dtype=np.float32), 1),
        (np.full((1, 1), np.nan, dtype=np.float32), None)
    ])
    def test_get_dbz_value(self, reflectivity: np.ndarray, expected_dbz: float):
        mock_tile_loader = MagicMock()
        mock_tile_loader.load = MagicMock()
        mock_tile_loader.load.return_value = PrecipitationData(reflectivity=reflectivity,
                                                               type=np.ones((1, 1), dtype=np.uint8))
        tile_reader = TileReader(mock_tile_loader)
        precip_value = tile_reader.get_dbz_value_by_tile(0, 0, 0, 0, 0)

        assert precip_value.dbz == expected_dbz
