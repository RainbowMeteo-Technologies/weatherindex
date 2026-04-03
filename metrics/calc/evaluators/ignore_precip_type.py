import pandas

from metrics.calc.evaluators.constants import PRECIP_THRESHOLD
from metrics.calc.metric_event import MetricEvent, create_metric_event


class IgnorePrecipTypeEvaluator:
    def __init__(self, threshold: float = PRECIP_THRESHOLD) -> None:
        self._threshold = threshold

    def __call__(self, sensor_observations: pandas.DataFrame, sensor_forecast: pandas.DataFrame) -> list[MetricEvent]:
        result = []

        max_row_observations = None
        for row in sensor_observations.itertuples():
            if max_row_observations is None or row.precip_rate > max_row_observations.precip_rate:

                max_row_observations = row

        observed_precip = max_row_observations.precip_rate > self._threshold

        max_row_forecast = None
        for row in sensor_forecast.itertuples():
            if max_row_forecast is None or row.precip_rate > max_row_forecast.precip_rate:
                max_row_forecast = row

        forecasted_precip = max_row_forecast.precip_rate > self._threshold

        result.append(create_metric_event(id=max_row_observations.id,
                                          timestamp=max_row_observations.timestamp,
                                          precip_type_observations=max_row_observations.precip_type,
                                          precip_rate_observations=max_row_observations.precip_rate,
                                          observed_precip=observed_precip,
                                          forecast_time=max_row_forecast.forecast_time,
                                          precip_type_forecast=max_row_forecast.precip_type,
                                          precip_rate_forecast=max_row_forecast.precip_rate,
                                          forecasted_precip=forecasted_precip))

        return result
