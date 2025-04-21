import pytest

from metrics.utils.coords import Coordinate, PixelCoordinate, TilePixel, coord_to_map_pixel, coord_to_tile_pixel


class TestCoords:

    @pytest.mark.parametrize("coord, zoom, expected_pixel", [
        (Coordinate(lon=-87.65, lat=41.85), 13, PixelCoordinate(x=537977, y=779672, zoom=13)),
        (Coordinate(lon=-100.65, lat=-80.2321), 4, PixelCoordinate(x=902, y=3651, zoom=4)),
        (Coordinate(lon=-100.65, lat=-80.2321), 17, PixelCoordinate(x=7395956, y=29913666, zoom=17)),
    ])
    def test_coord_to_map_pixel(self,
                                coord: Coordinate,
                                zoom: int,
                                expected_pixel: PixelCoordinate):

        assert coord_to_map_pixel(coord=coord,
                                  zoom=zoom,
                                  tile_size=256) == expected_pixel

    @pytest.mark.parametrize("coords, zoom, expected_pixel", [
        (Coordinate(lon=-87.65, lat=41.85), 13, TilePixel(tile_x=2101, tile_y=3045, px=121, py=152, zoom=13)),
        (Coordinate(lon=-100.65, lat=-80.2321), 4, TilePixel(tile_x=3, tile_y=14, px=134, py=67, zoom=4)),
        (Coordinate(lon=-100.65, lat=-80.2321), 17, TilePixel(tile_x=28890, tile_y=116850, px=116, py=66, zoom=17)),
    ])
    def test_coords_to_tile_pixel(self,
                                  coords: Coordinate,
                                  zoom: int,
                                  expected_pixel: TilePixel):

        assert coord_to_tile_pixel(coord=coords, zoom_level=zoom, tile_size=256) == expected_pixel
