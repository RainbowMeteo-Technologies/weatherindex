import pandas
import typing

from metrics.calc.evaluators import get_evaluator
from metrics.calc.events import CalculateMetrics, JobParams, Worker
from metrics.calc.forecast_manager import ForecastManager
from metrics.data_vendor import DataVendor


def create_calculate_metrics(forecast_vendor: DataVendor = DataVendor.AccuWeather,
                             observation_vendor: DataVendor = DataVendor.Metar,
                             sensor_selection_path: typing.Optional[str] = None,
                             forecast_offsets: typing.List[int] = [0, 60, 120],
                             evaluator: typing.Callable[[pandas.DataFrame, pandas.DataFrame],
                                                        list[list[any]]] = get_evaluator("rain_only"),
                             session_path: str = "test") -> CalculateMetrics:
    return CalculateMetrics(forecast_vendor=forecast_vendor,
                            observation_vendor=observation_vendor,
                            sensor_selection_path=sensor_selection_path,
                            forecast_offsets=forecast_offsets,
                            evaluator=evaluator,
                            session_path=session_path)


def create_worker(forecast_vendor: DataVendor = DataVendor.AccuWeather,
                  observation_vendor: DataVendor = DataVendor.Metar,
                  sensor_ids: typing.List[str] = [],
                  forecast_offsets: typing.List[int] = [0],
                  evaluator: typing.Callable[[pandas.DataFrame, pandas.DataFrame], list[list[any]]] = get_evaluator("rain_only"),
                  session_path: str = "test",
                  sensors_time_range: typing.Tuple[int, int] = (10800, 14400),
                  forecast_manager_cls: typing.Type[ForecastManager] = ForecastManager) -> Worker:
    return Worker(params=JobParams(forecast_vendor=forecast_vendor,
                                   observation_vendor=observation_vendor,
                                   sensor_ids=sensor_ids,
                                   forecast_offsets=forecast_offsets,
                                   evaluator=evaluator,
                                   session_path=session_path,
                                   time_range=sensors_time_range,
                                   forecast_manager_cls=forecast_manager_cls,
                                   output_path="test-output"))


def create_observations(data: typing.List[any]) -> pandas.DataFrame:
    return pandas.DataFrame(columns=["id", "precip_rate", "precip_type", "timestamp"],
                            data=data)


def create_forecast(data: typing.List[any]) -> pandas.DataFrame:
    return pandas.DataFrame(columns=["id", "precip_rate", "precip_type", "timestamp", "forecast_time"],
                            data=data)


def create_metrics(tp: int = 0, tn: int = 0, fp: int = 0, fn: int = 0) -> any:
    return (tp, tn, fp, fn)


def timestamp(timestamp: int, forecast_time: int = 0) -> int:
    return 15000 + timestamp + forecast_time


def create_metrics_result(data: typing.List[any], columns: typing.List[str]) -> pandas.DataFrame:
    return pandas.DataFrame(data=data, columns=columns)
