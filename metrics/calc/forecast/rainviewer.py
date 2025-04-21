from metrics.io.rainviewer import RainViewerTileLoader
from metrics.calc.forecast.tile_provider import TileProvider


class RainViewerProvider(TileProvider):

    FORECAST_STEP = 600

    def __init__(self, snapshots_path: str, snapshot_timestamp: int, max_forecast_time: int = 12 * 600) -> None:
        """
        Parameters
        ----------
        snapshots_path : str
            Path to folder with rainviewer snapshots
        snapshot_timestamp : int
            Timestamp of rainviewer tiles snapshot
        """
        super().__init__(snapshots_path=snapshots_path,
                         snapshot_timestamp=snapshot_timestamp,
                         tile_loader_class=RainViewerTileLoader,
                         max_forecast_time=max_forecast_time,
                         forecast_step=RainViewerProvider.FORECAST_STEP)
