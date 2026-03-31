import pandas

from metrics.calc.evaluators.ignore_precip_type import IgnorePrecipTypeEvaluator
from metrics.calc.evaluators.single_precip_type import RainOnlyEvaluator, SnowOnlyEvaluator

from typing import Callable


EVENTS_EVALUATORS = {
    "rain_only": RainOnlyEvaluator,
    "ignore_precip_type": IgnorePrecipTypeEvaluator,
    "snow_only": SnowOnlyEvaluator
}


SENSOR_METRICS_EVALUATOR = Callable[[pandas.DataFrame, pandas.DataFrame], list[list[any]]]


def get_evaluator(evaluator: str, evaluators=EVENTS_EVALUATORS, **kwargs) -> SENSOR_METRICS_EVALUATOR:
    return evaluators[evaluator](**kwargs)
