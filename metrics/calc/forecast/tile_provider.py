import os
import pandas
import typing

from metrics.calc.forecast.provider import ForecastProvider
from metrics.io.tile_loader import BaseTileLoader
from metrics.io.tile_reader import TileReader
from metrics.utils.coords import Coordinate
from metrics.utils.dbz import dbz_to_precipitation_rate
from metrics.utils.precipitation import PrecipitationType


class TileProvider(ForecastProvider):
    """Provider implementation for a tile data
    """

    RAIN_RATE_CONVERT_A: float = 200
    RAIN_RATE_CONVERT_B: float = 1.6

    SNOW_RATE_CONVERT_A: float = 200
    SNOW_RATE_CONVERT_B: float = 2.0

    def __init__(self,
                 snapshots_path: str,
                 snapshot_timestamp: int,
                 tile_loader_class: BaseTileLoader,
                 max_forecast_time: int = 3600,
                 forecast_step: int = 600) -> None:
        """
        Parameters
        ----------
        snapshots_path : str
            Path to folder with rainbow snapshots
        snapshot_timestamp : int
            Timestamp of rainbow tiles snapshot
        tile_loader_class : BaseTileLoader
            Class that inherits from BaseTileLoader that will be used to load data from a tile
        max_forecast_time : int
            Maximum forecast time in seconds
        forecast_step : int
            Forecast snapshots step in seconds
        """
        self._snapshot_timestamp = snapshot_timestamp
        self._max_forecast_time = max_forecast_time
        self._forecast_step = forecast_step
        self._tile_reader = None

        zip_path = os.path.join(snapshots_path, f"{snapshot_timestamp}.zip")
        if os.path.exists(zip_path):
            self._tile_reader = TileReader(tile_loader_class(zip_path=zip_path))

    def get_data_timestamp(self) -> int:
        """Returns snapshot timestamp of the data
        """
        return self._snapshot_timestamp

    @staticmethod
    def dbz_to_precipitation_rate(dbz: int, precip_type: PrecipitationType):
        rain_mmh = dbz_to_precipitation_rate(dbz=dbz,
                                             a=TileProvider.RAIN_RATE_CONVERT_A,
                                             b=TileProvider.RAIN_RATE_CONVERT_B)
        snow_mmh = dbz_to_precipitation_rate(dbz=dbz,
                                             a=TileProvider.SNOW_RATE_CONVERT_A,
                                             b=TileProvider.SNOW_RATE_CONVERT_B)

        if precip_type == PrecipitationType.RAIN:
            return rain_mmh
        elif precip_type == PrecipitationType.SNOW:
            return snow_mmh
        elif precip_type == PrecipitationType.MIX:
            return max(rain_mmh, snow_mmh)

        return dbz

    def load(self, sensors_table: pandas.DataFrame) -> typing.Optional[pandas.DataFrame]:
        result_data = []

        if self._tile_reader is not None:
            sensors_table = sensors_table.sort_values(by=["id", "lon", "lat"])

            forecast_time = 0
            while forecast_time <= self._max_forecast_time:
                for sensor in sensors_table.itertuples():
                    precip_value = self._tile_reader.get_dbz_value_by_coords(
                        coords=Coordinate(lon=sensor.lon, lat=sensor.lat),
                        offset=forecast_time // 60)

                    if precip_value is not None and precip_value.dbz is not None:
                        precip_rate = TileProvider.dbz_to_precipitation_rate(dbz=precip_value.dbz,
                                                                             precip_type=precip_value.precip_type)
                        result_data.append([
                            sensor.id,
                            precip_rate,
                            precip_value.precip_type.value,
                            self._snapshot_timestamp + forecast_time])

                forecast_time += self._forecast_step

        return pandas.DataFrame(data=result_data,
                                columns=["id", "precip_rate", "precip_type", "timestamp"])
