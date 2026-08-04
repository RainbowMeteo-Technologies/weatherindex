"""Constants for pre-merge forecast/observation metrics archives."""

FORECASTS_DIR_NAME = ".forecasts"
OBSERVATIONS_DIR_NAME = ".observations"
FORECAST_PARTIAL_PREFIX = "forecast_"
OBSERVATION_PARTIAL_PREFIX = "observation_"

# Fallback schemas when no partial frames were produced.
FORECAST_EXPORT_COLUMNS = ["id", "precip_rate", "precip_type", "timestamp", "forecast_time"]
OBSERVATION_EXPORT_COLUMNS = ["id", "precip_rate", "precip_type", "timestamp"]
