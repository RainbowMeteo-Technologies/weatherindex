import pandas

from metrics.calc.evaluators.constants import PRECIP_THRESHOLD


class IgnorePrecipTypeEvaluator:
    def __init__(self, threshold: float = PRECIP_THRESHOLD) -> None:
        self._threshold = threshold

    def __call__(self, sensor_observations: pandas.DataFrame, sensor_forecast: pandas.DataFrame) -> list[list[any]]:
        result = []

        max_row_observations = None
        for row in sensor_observations.itertuples():
            if max_row_observations is None or \
                    row.precip_rate > max_row_observations.precip_rate:

                max_row_observations = row

        observed_precip = max_row_observations.precip_rate > 0

        max_row_forecast = None
        for row in sensor_forecast.itertuples():
            if max_row_forecast is None or row.precip_rate > max_row_forecast.precip_rate:
                max_row_forecast = row

        forecasted_precip = max_row_forecast.precip_rate > 0

        result.append([max_row_observations.id,
                       max_row_observations.timestamp,
                       max_row_observations.precip_type,
                       max_row_observations.precip_rate,
                       observed_precip,
                       max_row_forecast.forecast_time,
                       max_row_forecast.precip_type,
                       max_row_forecast.precip_rate,
                       forecasted_precip])

        return result
