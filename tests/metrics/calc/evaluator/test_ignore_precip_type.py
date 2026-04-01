import pytest
import typing
import pandas

from metrics.calc.evaluators.ignore_precip_type import IgnorePrecipTypeEvaluator

from metrics.utils.metric import precision, recall, fscore
from metrics.utils.precipitation import PrecipitationType

from tests.utils.metrics.calc import create_worker, create_observations, create_forecast, create_metrics, create_metrics_result, timestamp


class TestIgnorePrecipTypeEvaluator:
    def get_evaluator(self) -> IgnorePrecipTypeEvaluator:
        return IgnorePrecipTypeEvaluator()

    @pytest.mark.parametrize("forecast_offsets, observations, forecast, expected_metrics", [
        (
            [0],
            create_observations([
                ("X", 10.0, PrecipitationType.SNOW.value, timestamp(0)),
                ("Y", 0.0, PrecipitationType.UNKNOWN.value, timestamp(0)),
                ("Z", 10.0, PrecipitationType.RAIN.value, timestamp(0))
            ]),
            create_forecast([
                ("X", 10.0, PrecipitationType.RAIN.value, timestamp(0), 0),
                ("Y", 0.0, PrecipitationType.MIX.value, timestamp(0), 0),
                ("Z", 10.0, PrecipitationType.SNOW.value, timestamp(0), 0)
            ]),
            create_metrics_result(data=[
                (0, "X", *create_metrics(tp=1)),
                (0, "Y", *create_metrics(tn=1)),
                (0, "Z", *create_metrics(tp=1))
            ], columns=("forecast_time", "sensor_id", "tp", "tn", "fp", "fn"))
        )
    ])
    def test_calculate_detailed(self,
                                forecast_offsets: typing.List[int],
                                observations: pandas.DataFrame,
                                forecast: pandas.DataFrame,
                                expected_metrics: pandas.DataFrame):
        worker = create_worker(forecast_offsets=forecast_offsets,
                               evaluator=self.get_evaluator())

        result = worker._calculate(forecast_times=forecast_offsets,
                                   observations=observations,
                                   forecast=forecast)

        merged_result = pandas.merge(expected_metrics,
                                     result,
                                     left_on=["forecast_time", "sensor_id"],
                                     right_on=["forecast_time", "id"],
                                     suffixes=("_expected", "_result"))

        for metric in ["tp", "tn", "fp", "fn"]:
            assert (merged_result[f"{metric}_expected"] == merged_result[f"{metric}_result"]).all(), \
                (f"Mismatch found in {metric} "
                 f"{merged_result[f'{metric}_expected']} != {merged_result[f'{metric}_result']}")

    @pytest.mark.parametrize("forecast_offsets, observations, forecast, expected_metrics", [
        (
            [0],
            create_observations([
                ("X", 10.0, PrecipitationType.SNOW.value, timestamp(0)),
                ("Y", 0.0, PrecipitationType.UNKNOWN.value, timestamp(0)),
                ("Z", 10.0, PrecipitationType.RAIN.value, timestamp(0))
            ]),
            create_forecast([
                # 2 TP, 1 TN -> 1.0 precision, 1.0 recall
                ("X", 10.0, PrecipitationType.RAIN.value, timestamp(0), 0),
                ("Y", 0.0, PrecipitationType.MIX.value, timestamp(0), 0),
                ("Z", 10.0, PrecipitationType.SNOW.value, timestamp(0), 0)
            ]),
            create_metrics_result(data=[
                (0, 1, 1, 1)
            ], columns=("forecast_time", "precision", "recall", "fscore"))
        )
    ])
    def test_precision_recall_fscore(self,
                                     forecast_offsets: typing.List[int],
                                     observations: pandas.DataFrame,
                                     forecast: pandas.DataFrame,
                                     expected_metrics: pandas.DataFrame):
        worker = create_worker(forecast_offsets=forecast_offsets, evaluator=self.get_evaluator())

        result = worker._calculate(forecast_times=forecast_offsets,
                                   observations=observations,
                                   forecast=forecast)

        result = result.groupby(["forecast_time"])[["tp", "tn", "fp", "fn"]].sum().reset_index()
        result["precision"] = result[["tp", "fp"]].apply(lambda row: precision(row["tp"], row["fp"]), axis=1)
        result["recall"] = result[["tp", "fn"]].apply(lambda row: recall(row["tp"], row["fn"]), axis=1)
        result["fscore"] = result[["precision", "recall"]].apply(
            lambda row: fscore(row["precision"], row["recall"]), axis=1)

        merged_result = pandas.merge(expected_metrics, result, on="forecast_time", suffixes=("_expected", "_result"))
        for metric in ["recall", "precision", "fscore"]:
            assert (merged_result[f"{metric}_expected"] == merged_result[f"{metric}_result"]).all(), \
                (f"Mismatch found in {metric} "
                 f"{merged_result[f'{metric}_expected']} != {merged_result[f'{metric}_result']}")
