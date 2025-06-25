import os
import pandas
import typing
import zipfile

from metrics.calc.forecast.rainviewer import RainViewerProvider
from metrics.calc.forecast.table_provider import TableProvider
from metrics.calc.forecast.provider import ForecastProvider
from metrics.data_vendor import BaseDataVendor, DataVendor

from metrics.session import Session
from metrics.utils.time import floor_timestamp

from rich.console import Console

console = Console()


class ForecastManager:
    """This class wraps access to data providers. It manages access to different timestamps of the data"""

    DATA_STEP = 600  # minimum step of forecast snasphots in seconds

    def __init__(self, data_vendor: BaseDataVendor, session: Session) -> None:

        self._data_vendor = data_vendor
        self._session = session

        self._providers: typing.Dict[int, ForecastProvider] = {}  # providers by timestamps

    def _create_data_provider(self, timestamp: int) -> ForecastProvider:
        if self._data_vendor.value == DataVendor.RainViewer.value:
            return RainViewerProvider(
                snapshots_path=os.path.join(self._session.data_folder, DataVendor.RainViewer.value),
                snapshot_timestamp=timestamp)
        elif self._data_vendor.value in [v.value for v in DataVendor]:
            snapshots_path = os.path.join(self._session.tables_folder, self._data_vendor.value)
            return TableProvider(tables_path=snapshots_path,
                                 snapshot_timestamp=timestamp)
        else:
            raise ValueError(f"Data vendor {self._data_vendor.value} is not supported")

    def _get_provider_for_timestamp(self, snapshot_timestamp: int) -> typing.Optional[ForecastProvider]:
        """Returns cached provider for specified snapshot_timestamp or creates new one

        Parameters
        ----------
        timestamp : int
            Snapshot timestamp

        Return
        ------
        Optional[VendorDataProvider]
            Returns VendorDataProvider for specified snapshot. If it wasn't created, then returns - `None`
        """
        found_provider = self._providers.get(snapshot_timestamp, None)
        if found_provider is None:
            try:
                new_provider = self._create_data_provider(timestamp=snapshot_timestamp)
                self._providers[snapshot_timestamp] = new_provider
                return new_provider
            except ValueError:
                return None
            except zipfile.BadZipFile:
                console.log(f"zipfile.BadZipFile getting provider {self._data_vendor.value} for {snapshot_timestamp}")
                return None

        return found_provider

    def load_forecast(self,
                      time_rage: typing.Tuple[int, int],
                      sensors_table: pandas.DataFrame) -> pandas.DataFrame:
        """Loads data for specified sensors and time range from provider

        Parameters
        ----------
        metric_timestamp : int
            Timestamp for which
        sensors_table : pandas.DataFrame
            Table of sensors. It should contains unique rows by sensor id. Has next columns: "id", "lon", "lat"

        Returns
        -------
        pandas.DataFrame
            Table with forecast for each sensor that has next columns: "id", "precip_rate", "precip_type", "forecast_time"
        """

        sensor_ids = set(sensors_table["id"].unique())
        unique_sensors_table = sensors_table.groupby("id").first().reset_index()

        curr_time = floor_timestamp(time_rage[0], ForecastManager.DATA_STEP)
        end_time = time_rage[1]

        loaded_forecasts = []
        while curr_time <= end_time:
            provider = self._get_provider_for_timestamp(curr_time)

            if provider:
                data = provider.load(sensors_table=unique_sensors_table)

                if data is not None:
                    assert "id" in data.columns
                    assert "precip_rate" in data.columns
                    assert "precip_type" in data.columns
                    assert "timestamp" in data.columns

                    data = data[data["id"].isin(sensor_ids)].copy()
                    data["forecast_time"] = data["timestamp"] - curr_time

                    loaded_forecasts.append(data)

            curr_time += ForecastManager.DATA_STEP

        return pandas.concat(loaded_forecasts)
