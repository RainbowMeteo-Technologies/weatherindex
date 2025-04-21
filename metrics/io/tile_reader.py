import mercantile
import numpy as np
import typing

from dataclasses import dataclass
from metrics.io.tile_loader import BaseTileLoader
from metrics.utils.coords import Coordinate, PixelCoordinate
from metrics.utils.precipitation import PrecipitationType


@dataclass
class PrecipValue:
    dbz: typing.Optional[float]  # dbz value
    precip_type: PrecipitationType  # precipitation type

    def is_rain(self) -> bool:
        return self.precip_type == PrecipitationType.RAIN


class TileReader:

    ZOOM_LEVEL = 7
    TILE_SIZE = 256

    def __init__(self, tile_loader: BaseTileLoader) -> None:
        self._tile_loader = tile_loader

    def _calculate_pixel_coordinates(self, coords: Coordinate) -> typing.Tuple[mercantile.Tile, PixelCoordinate]:
        tile_size_mult = TileReader.TILE_SIZE - 1
        tile = mercantile.tile(coords.lon, coords.lat, TileReader.ZOOM_LEVEL)

        # Calculate the x and y coordinates of the point relative to the top-left corner of the tile
        tile_bounds = mercantile.xy_bounds(tile.x, tile.y, TileReader.ZOOM_LEVEL)
        x, y = mercantile.xy(coords.lon, coords.lat)
        pixel_x = int(0.5 + (x - tile_bounds.left) / (tile_bounds.right - tile_bounds.left) * tile_size_mult)
        pixel_y = int(0.5 + ((1.0 - (y - tile_bounds.bottom) / (tile_bounds.top - tile_bounds.bottom)) * tile_size_mult))

        return (tile, PixelCoordinate(x=pixel_x, y=pixel_y, zoom=TileReader.ZOOM_LEVEL))

    def get_dbz_value_by_coords(self, coords: Coordinate, offset: int) -> PrecipValue:
        """Returns dbz value with precip type by coordinates and minutes offset
        """
        tile, pixel = self._calculate_pixel_coordinates(coords=coords)

        return self.get_dbz_value_by_tile(offset=offset,
                                          px=pixel.x,
                                          py=pixel.y,
                                          tile_x=tile.x,
                                          tile_y=tile.y)

    def get_dbz_value_by_tile(self, offset: int, px: int, py: int, tile_x: int, tile_y) -> PrecipValue:
        """Returns dbz value with precip type by tile coordinaes and pixel coordinates in tile
        Parameters
        ----------
        offset : int
            Forecast offset in minutes to load tile
        px : int
            X cooridnate of pixel to get value in tile
        py : int
            Y coordinate of pixel to get value in tile
        tile_x : int
            X croodinate of tile
        tile_y : int
            Y coordinate of tile

        Returns
        -------
        float
            Returns dbz value with precip type. When no coverage, then returns None
        """
        data = self._tile_loader.load(offset=offset, tile_x=tile_x, tile_y=tile_y)
        if data is None:
            return PrecipValue(dbz=None, precip_type=PrecipitationType.UNKNOWN)

        dbz = data.reflectivity[py, px]
        if np.isnan(dbz):
            dbz = None
        precip_type = PrecipitationType(data.type[py, px])
        return PrecipValue(dbz=dbz, precip_type=precip_type)
