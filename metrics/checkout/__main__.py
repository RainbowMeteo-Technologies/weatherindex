import argparse

from metrics.checkout.data_source import ForecastSourcesInfo, ObservationSourcesInfo
from metrics.checkout.checkout import checkout


def _run_checkout(args: argparse.Namespace):
    forecasts = ForecastSourcesInfo(s3_uri_rainviewer=args.s3_uri_rainviewer,
                                    s3_uri_wk=args.s3_uri_wk,
                                    s3_uri_accuweather=args.s3_uri_accuweather,
                                    s3_uri_tomorrowio=args.s3_uri_tomorrowio,
                                    s3_uri_vaisala=args.s3_uri_vaisala,
                                    s3_uri_rainbowai=args.s3_uri_rainbowai,
                                    s3_uri_weathercompany=args.s3_uri_weathercompany)

    observations = ObservationSourcesInfo(s3_uri_metar=args.s3_uri_metar_data)

    checkout(start_time=args.start_time,
             end_time=args.end_time,
             session_path=args.session_path,
             session_clear=args.session_clear,
             forecasts_source=forecasts,
             observations_source=observations,
             forecast_range=args.forecast_range)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tool generates metrics based on sensors data")

    subparsers = parser.add_subparsers(help="Available commands")

    common = parser.add_argument_group("Common parameters")
    common.add_argument("--process-num", type=int, dest="process_num", default=None, required=False,
                        help="Number of processes for multiprocessing")

    parser.add_argument("--session-path", type=str, dest="session_path", required=True,
                        help="Path to directory where to download required files")
    parser.add_argument("--session-clear", dest="session_clear", action="store_true",
                        help="Flag to remove old session if it already exists")
    parser.add_argument("--start-time", type=int, dest="start_time", required=True,
                        help="Start timestamp")
    parser.add_argument("--end-time", type=int, dest="end_time", required=True,
                        help="End timestamp")
    parser.add_argument("--forecast-range", type=int, dest="forecast_range", required=False, default=7800,
                        help="Forecast range in seconds")

    sensor_group = parser.add_argument_group(title="Sensors")
    sensor_group.add_argument("--s3-uri-metar-data", type=str, dest="s3_uri_metar_data", required=False, default=None,
                              help="S3 uri where to get metar data")

    # data
    s3_group = parser.add_argument_group(title="Data URI")
    s3_group.add_argument("--s3-uri-rainviewer", type=str, dest="s3_uri_rainviewer", required=False, default=None,
                          help="S3 uri where to get rainviewer forecast")
    s3_group.add_argument("--s3-uri-wk", type=str, dest="s3_uri_wk", required=False, default=None,
                          help="S3 uri where to get weather kit forecast")
    s3_group.add_argument("--s3-uri-accuweather", type=str, dest="s3_uri_accuweather", required=False, default=None,
                          help="S3 uri where to get accuweather forecast")
    s3_group.add_argument("--s3-uri-tomorrowio", type=str, dest="s3_uri_tomorrowio", required=False, default=None,
                          help="S3 uri where to get tomorrow io forecast")
    s3_group.add_argument("--s3-uri-vaisala", type=str, dest="s3_uri_vaisala", required=False, default=None,
                          help="S3 uri where to get vaisala forecast")
    s3_group.add_argument("--s3-uri-rainbowai", type=str, dest="s3_uri_rainbowai", required=False, default=None,
                          help="S3 uri where to get rainbowai forecast")
    s3_group.add_argument("--s3-uri-weathercompany", type=str, dest="s3_uri_weathercompany",
                          required=False, default=None,
                          help="S3 uri where to get WeatherCompany forecast")

    parser.set_defaults(func=_run_checkout)

    args = parser.parse_args()
    args.func(args)
