import argparse
import csv
import geopandas as gpd
import math
import numpy as np
import os
import pandas
import typing
import zipfile

from metrics.utils.coords import coord_to_map_pixel, Coordinate
from metrics.utils.precipitation import PrecipitationData
from shapely.geometry import Point
from rich.console import Console
from rich.progress import Progress

CURRENT_DIR = os.path.dirname(__file__)
TILE_SIZE = 256
ZOOM = 7

console = Console()


class Geocoder:

    def __init__(self) -> None:
        self._world = gpd.read_file(os.path.join(CURRENT_DIR, "world-administrative-boundaries.zip"))

    def get_country(self, lon: float, lat: float) -> str:
        point = Point(lon, lat)

        # spatially join the point with the world map to get the country name
        country = gpd.sjoin(gpd.GeoDataFrame(geometry=[point], crs="EPSG:4326"), self._world, predicate="within")

        if len(country.values) > 1:
            print(country)
            print(lon, lat)

        if len(country.values) == 0:
            return None

        assert len(country.values) <= 1
        code = country["iso3"].values[0]
        return code


def _tile_index(tx: int, ty: int, zoom: int = ZOOM) -> int:
    return tx * (2 ** zoom) + ty


def main(bbox: typing.Tuple[float, float, float, float],
         grid_size: typing.Tuple[int, int],
         sensor_per_cell: int,
         sensor_list_path: str,
         output_file: str,
         include_countries: typing.List[str],
         exclude_countries: typing.List[str]):

    console.log(f"Processing sensors:\n"
                f"- sensor list path: {sensor_list_path}\n"
                f"- exclude countries: {exclude_countries}\n"
                f"- include countries: {include_countries}\n"
                f"- bbox: {bbox}\n"
                f"- grid: {grid_size}\n")

    geocoder = Geocoder()

    data = pandas.read_csv(sensor_list_path)

    data = data.sort_values(by="count", ascending=False)

    grid_west, grid_north, grid_east, grid_south = bbox

    grid_width_cells, grid_height_cells = grid_size
    sensor_per_cell = 2

    found_sensors = np.zeros((grid_height_cells, grid_width_cells), dtype=np.uint8)
    total_sensors_num = grid_width_cells * grid_height_cells * sensor_per_cell
    print(f"Total sensors: {total_sensors_num}")

    def _is_inside_bbox(lon: float, lat: float) -> bool:
        return lon > grid_west and lon < grid_east \
            and lat > grid_south and lat < grid_north

    def _get_cell_index(lon: float, lat: float) -> typing.Tuple[int, int]:
        step_x = (grid_east - grid_west) / grid_width_cells
        step_y = (grid_north - grid_south) / grid_height_cells

        return (int(math.floor((lon - grid_west) / step_x)),
                int(math.floor((lat - grid_south) / step_y)))

    def _should_accept_sensor(lon: float, lat: float) -> bool:

        if len(include_countries) > 0:
            return geocoder.get_country(lon=lon, lat=lat) in include_countries

        passed_exclude = True
        if len(exclude_countries) > 0:
            country = geocoder.get_country(lon=lon, lat=lat)
            if country is None or not isinstance(country, str) or len(country) < 3:
                passed_exclude = False
            else:
                passed_exclude = country not in exclude_countries

        return passed_exclude

    with open(output_file, "w") as file:
        writer = csv.writer(file)
        writer.writerow(["id", "lon", "lat", "count", "country"])

        with Progress() as progress:
            task = progress.add_task("Found", total=len(data))

            for _, row in enumerate(data.itertuples()):
                if _is_inside_bbox(lon=row.lon, lat=row.lat):

                    gx, gy = _get_cell_index(lon=row.lon, lat=row.lat)

                    if found_sensors[gy, gx] < sensor_per_cell and _should_accept_sensor(lon=row.lon, lat=row.lat):
                        found_sensors[gy, gx] += 1
                        country = geocoder.get_country(lon=row.lon, lat=row.lat)
                        writer.writerow([row.id, row.lon, row.lat, row.count, country])

                progress.update(task, advance=1, description=f"Found: {found_sensors.sum()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser("Tool to select specified number of sensors placed with normal distribution")

    parser.add_argument("--west", type=float, default=-180, help="West border of bounding box")
    parser.add_argument("--north", type=float, default=90, help="North border of bounding box")
    parser.add_argument("--east", type=float, default=180, help="East border of bounding box")
    parser.add_argument("--south", type=float, default=-90, help="South border of bounding box")
    parser.add_argument("--grid-width", dest="grid_width", type=int, default=360,
                        help="Number of grid cells by X-axis")
    parser.add_argument("--grid-height", dest="grid_height", type=int, default=180,
                        help="Number of grid cells by Y-axis")
    parser.add_argument("--sensors-per-cell", dest="sensors_per_cell", type=int, default=2,
                        help="Number of sensors per one cell")
    parser.add_argument("--sensor-list-path", dest="sensor_list_path", type=str,
                        default=os.path.join(CURRENT_DIR, "sensors.metar.csv.zip"),
                        help="Path to the archive with sensors list")

    parser.add_argument("--output", type=str, required=True, help="Path to the output CSV file")

    parser.add_argument("--include-countries", dest="include_countries", nargs="+", type=str, default=[],
                        help=("List of alpha 3 country codes from which include sensors. "
                              "See https: // www.iban.com/country-codes for more information"))

    parser.add_argument("--exclude-countries", dest="exclude_countries", nargs="+", type=str, default=[],
                        help=("List of alpha 3 country codes from which exclude sensors. "
                              "See https://www.iban.com/country-codes for more information"))

    args = parser.parse_args()

    main(bbox=(args.west, args.north, args.east, args.south),
         grid_size=(args.grid_width, args.grid_height),
         sensor_per_cell=args.sensors_per_cell,
         sensor_list_path=args.sensor_list_path,
         output_file=args.output,
         include_countries=args.include_countries,
         exclude_countries=args.exclude_countries)
