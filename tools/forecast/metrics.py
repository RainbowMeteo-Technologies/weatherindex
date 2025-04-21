import prometheus_client


FORECAST_DATA_DOWNLOAD_STATUS = prometheus_client.Gauge(
    "rmt_metrics_forecast_download_status",
    "Forecast data download status: 1 - if exists, 0 - if not.",
    labelnames=["forecast_provider", "lat", "lon"])


class Metrics:
    @staticmethod
    def set_forecast_download_status(forecast_provider: str, lat: float, lon: float, status: int):
        FORECAST_DATA_DOWNLOAD_STATUS.labels(forecast_provider, f"{lat:.3f}", f"{lon:.3f}").set(status)
