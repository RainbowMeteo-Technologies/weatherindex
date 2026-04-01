import pandas

from metrics.calc.evaluators.constants import RAIN_THRESHOLD, SNOW_THRESHOLD
from metrics.calc.metric_event import MetricEvent, create_metric_event

from metrics.utils.precipitation import PrecipitationType


class SinglePrecipTypeEvaluator:
    def __init__(self, precip_type: PrecipitationType, threshold: float) -> None:
        self._precip_type = precip_type
        self._threshold = threshold

    def __call__(self, sensor_observations: pandas.DataFrame, sensor_forecast: pandas.DataFrame) -> list[MetricEvent]:
        """Calculates event metrics for a sensor

        Parameters
        ----------
        sensor_observations : pandas.DataFrame
            Observations data for a sensor
        sensor_forecast : pandas.DataFrame
            Forecast data for a sensor
        """

        result = []

        observed_rain = False
        for obs_row in sensor_observations.itertuples():
            if obs_row.precip_type == self._precip_type.value and obs_row.precip_rate > self._threshold:
                observed_rain = True
                break

        forecasted_rain = False
        for forecast_row in sensor_forecast.itertuples():
            if forecast_row.precip_type == self._precip_type.value and forecast_row.precip_rate > self._threshold:
                forecasted_rain = True
                break

        result.append(create_metric_event(id=obs_row.id,
                                          timestamp=obs_row.timestamp,
                                          precip_type_observations=obs_row.precip_type,
                                          precip_rate_observations=obs_row.precip_rate,
                                          observed_precip=observed_rain,
                                          forecast_time=forecast_row.forecast_time,
                                          precip_type_forecast=forecast_row.precip_type,
                                          precip_rate_forecast=forecast_row.precip_rate,
                                          forecasted_precip=forecasted_rain))

        return result


class RainOnlyEvaluator(SinglePrecipTypeEvaluator):
    def __init__(self, threshold: float = RAIN_THRESHOLD) -> None:
        super().__init__(PrecipitationType.RAIN, threshold)


class SnowOnlyEvaluator(SinglePrecipTypeEvaluator):
    def __init__(self, threshold: float = SNOW_THRESHOLD) -> None:
        super().__init__(PrecipitationType.SNOW, threshold)
