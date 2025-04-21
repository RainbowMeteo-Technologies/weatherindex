import pandas

from abc import abstractmethod


class ForecastProvider:

    @abstractmethod
    def get_data_timestamp(self) -> int:
        """Returns snapshot timestamp of the data
        """
        raise NotImplementedError("Override this function")

    @abstractmethod
    def load(self, sensors_table) -> pandas.DataFrame:
        """Returns precipitation rate for specified sensor and greater than prob_threshold

        Parameters
        ----------
        sensors_table : pandas.DataFrame
            Table of sensors. It should contains unique rows by sensor id. Has next columns: "id", "lon", "lat"

        Returns
        -------
        pandas.DataFrame
            Table with forecast for each sensor that has next columns: "id", "precip_rate", "precip_type", "timestamp"
        """
        raise NotImplementedError("Override this function")

    def _filter_by_sensors(self,
                           sensors_table: pandas.DataFrame,
                           data: pandas.DataFrame) -> pandas.DataFrame:
        """Filters data table by sensors. Leaves only `data` for specified sensor id's.
        Both tables should have `id` column.

        Parameters
        ----------
        sensors_table : pandas.DataFrame
            Table of sensors
        data : pandas.DataFrame
            Data table to filter

        Returns
        -------
        pandas.DataFrame
            Returns filtered data table. This table contains only rows with id's that exists in `sensors_table`
        """
        sensor_ids = set(sensors_table["id"].unique())
        return data[data["id"].isin(sensor_ids)]
