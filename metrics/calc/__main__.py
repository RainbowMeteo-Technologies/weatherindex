import argparse

from metrics.data_vendor import DataVendor
from metrics.calc.events import calc_events

from metrics.utils.precipitation import PrecipitationType
from rich.console import Console

from weatherindex.metrics.calc.evaluators import EVENTS_EVALUATORS


console = Console()


def _run_events(session_path: str,
                forecast_vendor: DataVendor,
                observation_vendor: DataVendor,
                offsets: str,
                evaluator: str,
                output_csv: str,
                observations_offset: int,
                process_num: int,
                filter_sensors_dir: str):
    console.log(f"Run [green]calculate[/green] command:\n"
                f"- session_path = {session_path}\n"
                f"- forecast_vendor = {forecast_vendor}\n"
                f"- observation_vendors = {observation_vendor}\n"
                f"- offsets = {offsets}\n"
                f"- evaluator = {evaluator}\n"
                f"- output_csv = {output_csv}\n"
                f"- observations_offset = {observations_offset}\n"
                f"- process_num = {process_num}\n"
                f"- filter_sensors_dir = {filter_sensors_dir}\n")

    calc_events(forecast_vendor=forecast_vendor,
                observation_vendor=observation_vendor,
                forecast_offsets=[int(v) * 60 for v in offsets.split(" ")],
                observations_offset=observations_offset,
                evaluator=evaluator,
                sensor_selection_path=filter_sensors_dir,
                process_num=process_num,
                output_csv=output_csv)


def _parse_event_args(subparsers: argparse._SubParsersAction):
    parser = subparsers.add_parser(
        name="events",
        help="Calculates event based metrics like (f1 score, recall, precision and etc.)")

    parser.add_argument("--offsets", type=str, default="0 10 20 30 40 50 60",
                        help="List of offsets to calculate metrics")
    parser.add_argument("--forecast-vendor", type=DataVendor, required=True,
                        help="Data vendor to compare with sensors")
    parser.add_argument("--observation-vendor", type=DataVendor, required=True,
                        help="Sensors vendor to compare with data")
    parser.add_argument("--filter-sensors-dir", type=str, default=None,
                        help=("Path to a directory with parquet tables. "
                              "If this argument exists, then only sensors id's found in directory would be used."
                              "Sensor id is and `id` field in a parquet table"))

    parser.set_defaults(func=_run_events)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calculates precision, recall, f1 score metrics")

    parser.add_argument("--session-path", type=str, required=True, help="Path to session directory")
    parser.add_argument("--process-num", type=int, default=None, help="Number of parallel processes")
    parser.add_argument("--threshold", type=float, default=0.1, help="Threshold in mm/h")
    parser.add_argument("--evaluator", type=str, default="rain_only",
                        choices=list(EVENTS_EVALUATORS.keys()), help="Evaluator to use")
    parser.add_argument("--output-csv", type=str, required=True, help="Output CSV file")
    parser.add_argument("--observations-offset", type=int, default=0, required=False,
                        help="Events window offset comparing to forecast")

    subparsers = parser.add_subparsers(title="Commands", required=True)

    _parse_event_args(subparsers)

    args = parser.parse_args()
    args.func(**vars(args))
