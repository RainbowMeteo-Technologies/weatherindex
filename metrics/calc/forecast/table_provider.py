import os
import pandas
import typing

from metrics.calc.forecast.provider import ForecastProvider


class TableProvider(ForecastProvider):

    def __init__(self, tables_path: str, snapshot_timestamp: int) -> None:
        """
        Parameters
        ----------
        tables_path : str
            Path to directory with parquet tables
        snapshot_timestamp : int
            Timestamp of rainbow tiles snapshot
        """

        self._snapshot_timestamp = snapshot_timestamp
        self._table = None
        table_path = os.path.join(tables_path, f"{snapshot_timestamp}.parquet")
        if os.path.exists(table_path):
            self._table = pandas.read_parquet(table_path)

    def get_data_timestamp(self) -> int:
        """Returns snapshot timestamp of the data
        """
        return self._snapshot_timestamp

    def load(self, sensors_table: pandas.DataFrame) -> typing.Optional[pandas.DataFrame]:
        """See DataProviderInterface.load"""
        if self._table is None:
            return None

        return self._filter_by_sensors(sensors_table=sensors_table,
                                       data=self._table)
