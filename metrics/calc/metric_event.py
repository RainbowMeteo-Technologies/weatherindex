from collections import namedtuple


MetricEvent = namedtuple("MetricEvent",
                         ["id",
                          "timestamp",
                          "precip_type_observations",
                          "precip_rate_observations",
                          "observed_precip",
                          "forecast_time",
                          "precip_type_forecast",
                          "precip_rate_forecast",
                          "forecasted_precip"])


def create_metric_event(id: str,
                        timestamp: int,
                        precip_type_observations: int,
                        precip_rate_observations: float,
                        observed_precip: bool,
                        forecast_time: int,
                        precip_type_forecast: int,
                        precip_rate_forecast: float,
                        forecasted_precip: bool) -> MetricEvent:
    return MetricEvent(id=id,
                       timestamp=timestamp,
                       precip_type_observations=precip_type_observations,
                       precip_rate_observations=precip_rate_observations,
                       observed_precip=observed_precip,
                       forecast_time=forecast_time,
                       precip_type_forecast=precip_type_forecast,
                       precip_rate_forecast=precip_rate_forecast,
                       forecasted_precip=forecasted_precip)
