"""Shared metrics package constants."""

FORECASTS_DIR_NAME = ".forecasts"
OBSERVATIONS_DIR_NAME = ".observations"

# Fallback schemas when no partial frames were produced.
FORECAST_EXPORT_COLUMNS = ["id", "precip_rate", "precip_type", "timestamp", "forecast_time"]
OBSERVATION_EXPORT_COLUMNS = ["id", "precip_rate", "precip_type", "timestamp"]
