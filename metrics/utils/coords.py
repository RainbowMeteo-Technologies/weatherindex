import math

from dataclasses import dataclass

WEB_MERCATOR_BOUND = 85.06


@dataclass(frozen=True)
class Coordinate:
    lon: float
    lat: float

    def is_valid(self) -> bool:
        return (-180.0 <= self.lon <= 180.0) \
            and (-90.0 <= self.lat <= 90.0)


@dataclass(frozen=True)
class PixelCoordinate:
    x: int
    y: int
    zoom: int


@dataclass(frozen=True)
class TilePixel:
    tile_x: int     # x coordinate of the tile
    tile_y: int     # y coordinate of the tile
    px: int         # x coordinate of the pixel in the tile
    py: int         # y coordinate of the pixel in the tile
    zoom: int       # zoom level


def coord_to_map_pixel(coord: Coordinate,
                       zoom: int,
                       tile_size: int) -> PixelCoordinate:
    """Converts GPS coordinates into pixel coordinates
    Implementation based on https://developers.google.com/maps/documentation/javascript/examples/map-coordinates
    """
    def clamp(min_value, value, max_value):
        return min(max_value, max(min_value, value))

    scale = 2 ** zoom

    # clamp latitude to web mercator
    lat = clamp(-WEB_MERCATOR_BOUND, coord.lat, WEB_MERCATOR_BOUND)

    siny = math.sin((lat * math.pi) / 180.0)

    x = int(scale * tile_size * (0.5 + coord.lon / 360.0))
    y = int(scale * tile_size * (0.5 - math.log((1 + siny) / (1 - siny)) / (4 * math.pi)))

    # webmercator clamps lat value in range [-85.06; 85.06] degrees,
    # but on edge we get values out of pixel bounds
    y = clamp(0, y, scale * tile_size)

    return PixelCoordinate(x=x, y=y, zoom=zoom)


def coord_to_tile_pixel(coord: Coordinate, zoom_level: int, tile_size: int) -> TilePixel:
    """Calculates pixel coordinates in the tile for specified lon, lat coorainates

    Parameters
    ----------
    coord : Coordinate
        Coordinate to transform
    zoom : int
        Zoom level
    tile_size : int
        Tile size in pixels

    Returns
    -------
    TilePixel
        Tile coordinates and pixel coordinates in this tile
    """
    world_pixel = coord_to_map_pixel(coord=coord,
                                     zoom=zoom_level,
                                     tile_size=tile_size)

    return TilePixel(px=world_pixel.x % tile_size,
                     py=world_pixel.y % tile_size,
                     tile_x=world_pixel.x // tile_size,
                     tile_y=world_pixel.y // tile_size,
                     zoom=zoom_level)
