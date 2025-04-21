import argparse
import os

from metrics.data_vendor import DataVendor
from metrics.calc.events import CalculateMetrics

from metrics.utils.precipitation import PrecipitationType
from rich.console import Console


console = Console()


def _run_events(args: argparse.Namespace):
    console.log(f"Run [green]calculate[/green] command:\n"
                f"- session_path = {args.session_path}\n"
                f"- forecast_vendor = {args.forecast_vendor}\n"
                f"- observation_vendors = {args.observation_vendor}\n"
                f"- threshold = {args.threshold}\n"
                f"- precip_types = {args.precip_types}\n"
                f"- forecast_offsets = {args.offsets}\n"
                f"- observations_offset = {args.observations_offset}\n"
                f"- sensor_selection_path = {args.filter_sensors_dir}\n"
                f"- process_num = {args.process_num}\n")

    calculator = CalculateMetrics(
        forecast_vendor=DataVendor(args.forecast_vendor),
        observation_vendor=DataVendor(args.observation_vendor),
        session_path=args.session_path,
        forecast_offsets=[int(v) * 60 for v in args.offsets.split(" ")],
        threshold=args.threshold,
        precip_types=[PrecipitationType[t.upper()] for t in args.precip_types],
        observations_offset=args.observations_offset,
        sensor_selection_path=args.filter_sensors_dir
    )

    os.makedirs(os.path.dirname(args.output_csv), exist_ok=True)
    calculator.calculate(output_csv=args.output_csv,
                         process_num=args.process_num)


def _parse_event_args(subparsers: argparse._SubParsersAction):
    parser = subparsers.add_parser(
        name="events",
        help="Calculates event based metrics like (f1 score, recall, precision and etc.)")

    parser.add_argument("--offsets", type=str, default="0 10 20 30 40 50 60",
                        help="List of offsets to calculate metrics")
    parser.add_argument("--forecast-vendor", dest="forecast_vendor", type=str, required=True,
                        choices=[value.value for value in DataVendor],
                        help="Data vendor to compare with sensors")
    parser.add_argument("--observation-vendor", dest="observation_vendor", type=str, required=True,
                        choices=[value.value for value in DataVendor],
                        help="Sensors vendor to compare with data")
    parser.add_argument("--filter-sensors-dir", dest="filter_sensors_dir", type=str, default=None,
                        help=("Path to a directory with parquet tables. "
                              "If this argument exists, then only sensors id's found in directory would be used."
                              "Sensor id is and `id` field in a parquet table"))

    parser.set_defaults(func=_run_events)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calculates precision, recall, f1 score metrics")

    parser.add_argument("--session-path", dest="session_path", type=str, required=True,
                        help="Path to session directory")
    parser.add_argument("--process-num", dest="process_num", type=int, default=None,
                        help="Number of parallel processes")
    parser.add_argument("--threshold", dest="threshold", type=float, default=0.1,
                        help="Threshold in mm/h")
    parser.add_argument("--precip-types", dest="precip_types", nargs="+", type=str,
                        help="Precip types of precipitation event",
                        choices=[t.name.lower() for t in PrecipitationType], default=["rain"])
    parser.add_argument("--output-csv", type=str, dest="output_csv", required=True,
                        help="Output CSV file")
    parser.add_argument("--observations-offset", dest="observations_offset", type=int, default=0,
                        required=False, help="Events window offset comparing to forecast")

    subparsers = parser.add_subparsers(title="Commands", required=True)

    _parse_event_args(subparsers)

    args = parser.parse_args()
    args.func(args)
