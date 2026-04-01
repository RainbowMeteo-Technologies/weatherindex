import pandas

from metrics.calc.evaluators.ignore_precip_type import IgnorePrecipTypeEvaluator
from metrics.calc.evaluators.single_precip_type import RainOnlyEvaluator, SnowOnlyEvaluator

from metrics.calc.metric_event import MetricEvent

from typing import Callable


SENSOR_METRICS_EVALUATOR = Callable[[pandas.DataFrame, pandas.DataFrame], list[MetricEvent]]
EVALUATORS_REGISTY = dict[str, SENSOR_METRICS_EVALUATOR]


EVENTS_EVALUATORS: EVALUATORS_REGISTY = {
    "rain_only": RainOnlyEvaluator,
    "ignore_precip_type": IgnorePrecipTypeEvaluator,
    "snow_only": SnowOnlyEvaluator
}


def get_evaluator(evaluator: str,
                  evaluators: EVALUATORS_REGISTY = EVENTS_EVALUATORS,
                  **kwargs) -> SENSOR_METRICS_EVALUATOR:
    return evaluators[evaluator](**kwargs)
