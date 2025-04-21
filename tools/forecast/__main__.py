import aioboto3
import argparse
import asyncio
import os
import shutil
import typing

from datetime import datetime

from forecast.client.accuweather import AccuWeather
from forecast.client.microsoft import Microsoft
from forecast.client.myradar import MyRadar
from forecast.client.openweather import OpenWeather
from forecast.client.rainbow import Rainbow
from forecast.client.rainviewer import RainViewer
from forecast.client.tomorrowio import TomorrowIo, TOMORROW_FORECAST_TYPES
from forecast.client.vaisala import Vaisala
from forecast.client.weather_company import WeatherCompany
from forecast.client.weather_kit import WeatherKit, Token, TokenParams

from forecast.sensor import Sensor

from rich.console import Console
from urllib.parse import urlparse


DOWNLOAD_PERIOD = 3600
WK_FORECAST_TYPES = ["hour", "day"]

console = Console()


def get_current_time() -> int:
    return int(datetime.now().timestamp())


def align_time(timestamp: int, period: int = 3600) -> int:
    return timestamp - (timestamp % period)


class ForecastDownloader:
    def __init__(self,
                 download_path: str,
                 s3_uri: str,
                 process_num: int,
                 download_period: int,
                 client_initializer: typing.Callable[[], typing.Any],
                 keep_local_snapshots: bool = False):
        self._download_path = download_path
        self._s3_uri = s3_uri
        self._process_num = process_num
        self._download_period = download_period
        self._client_initializer = client_initializer
        self._keep_local_snapshots = keep_local_snapshots
        self._last_upload = get_current_time()

    async def _upload_snapshot(self, snapshot_path: str):
        # Parse the URL
        parsed_url = urlparse(self._s3_uri)

        # Get the bucket name (netloc) and object key (path)
        bucket_name = parsed_url.netloc
        object_key = parsed_url.path[1:]

        upload_file_name = os.path.basename(snapshot_path)

        file_stats = os.stat(snapshot_path)
        console.log(f"Uploading size {file_stats.st_size / 1024 / 1024:0.2f} MB")

        async with aioboto3.Session().client("s3") as s3:
            await s3.upload_file(snapshot_path, bucket_name, object_key + upload_file_name)

    async def run(self, snapshots_to_download: typing.Optional[int] = None):
        def keep_running(downloaded_snapshots: int) -> bool:
            return snapshots_to_download is None or downloaded_snapshots < snapshots_to_download

        console.log(f"Start download sensors:\n"
                    f"- destination bucket: {self._s3_uri}\n")

        downloaded_snapshots = 0

        while keep_running(downloaded_snapshots):
            current_time = get_current_time()
            current_snapshot = align_time(current_time, period=self._download_period)
            next_snapshot = current_snapshot + self._download_period

            # wait download
            wait_time = next_snapshot - current_time
            console.log(f"Next download in {wait_time} seconds. Snapshot - {next_snapshot}")
            await asyncio.sleep(wait_time)

            self._last_upload = get_current_time()

            client = self._client_initializer()
            snapshot_path = os.path.join(self._download_path, str(next_snapshot))

            shutil.rmtree(snapshot_path, ignore_errors=True)
            os.makedirs(snapshot_path, exist_ok=False)

            await client.get_forecast(download_path=snapshot_path,
                                      process_num=self._process_num)

            # compress
            shutil.make_archive(base_name=snapshot_path,
                                format="zip",
                                root_dir=self._download_path,
                                base_dir=str(next_snapshot))
            archive_path = f"{snapshot_path}.zip"

            if self._s3_uri is not None:
                console.log(f"Uploading snapshot {next_snapshot} to S3")
                await self._upload_snapshot(snapshot_path=archive_path)

            downloaded_snapshots += 1
            if snapshots_to_download is not None:
                console.log(f"Snapshot was collected - {downloaded_snapshots} of {snapshots_to_download}")
            else:
                console.log(f"Snapshot was collected")

            if not self._keep_local_snapshots:
                console.log(f"Remove:\n - {snapshot_path}\n - {archive_path}")

                shutil.rmtree(snapshot_path)
                os.remove(archive_path)

            self._last_upload = get_current_time()


def _create_wk(args: argparse.Namespace) -> WeatherKit:
    if args.forecast_type == "hour":
        datasets = "forecastNextHour"
    elif args.forecast_type == "day":
        datasets = "currentWeather,forecastHourly"

    with open(args.token, "r") as file:
        token_params = TokenParams.from_json(file)
        token = Token.generate(token_params)

    sensors = Sensor.from_csv(sensors_path=args.sensors,
                              include_countries=args.include_countries)

    return WeatherKit(token=token.token,
                      datasets=datasets,
                      sensors=sensors)


def _create_accuweather(args: argparse.Namespace) -> AccuWeather:
    sensors = Sensor.from_csv(sensors_path=args.sensors,
                              include_countries=args.include_countries)

    return AccuWeather(token=args.token,
                       sensors=sensors)


def _create_myradar(args: argparse.Namespace) -> MyRadar:
    sensors = Sensor.from_csv(sensors_path=args.sensors,
                              include_countries=args.include_countries)

    return MyRadar(sub_key=args.key,
                   sensors=sensors)


def _create_microsoft(args: argparse.Namespace) -> Microsoft:
    sensors = Sensor.from_csv(sensors_path=args.sensors,
                              include_countries=args.include_countries)

    return Microsoft(cliend_id=args.client_id,
                     subscription_key=args.subscription_key,
                     sensors=sensors)


def _create_tomorrowio(args: argparse.Namespace) -> TomorrowIo:
    sensors = Sensor.from_csv(sensors_path=args.sensors,
                              include_countries=args.include_countries)

    return TomorrowIo(token=args.token,
                      forecast_type=args.forecast_type,
                      sensors=sensors)


def _create_viasala(args: argparse.Namespace) -> Vaisala:
    sensors = Sensor.from_csv(sensors_path=args.sensors,
                              include_countries=args.include_countries)

    return Vaisala(client_id=args.client_id,
                   client_secret=args.client_secret,
                   sensors=sensors)


def _create_open_weather(args: argparse.Namespace) -> OpenWeather:
    sensors = Sensor.from_csv(sensors_path=args.sensors,
                              include_countries=args.include_countries)

    return OpenWeather(token=args.token,
                       sensors=sensors)


def _create_rainbow(args: argparse.Namespace) -> Rainbow:
    sensors = Sensor.from_csv(sensors_path=args.sensors,
                              include_countries=args.include_countries)

    return Rainbow(token=args.token,
                   sensors=sensors)


def _create_rainviewer(args: argparse.Namespace) -> RainViewer:
    return RainViewer(token=args.token, zoom=args.zoom)


def _create_weathercompany(args: argparse.Namespace) -> WeatherCompany:
    sensors = Sensor.from_csv(sensors_path=args.sensors,
                              include_countries=args.include_countries)

    return WeatherCompany(token=args.token,
                          sensors=sensors)


def _add_sensors_params(parser: argparse.ArgumentParser):
    parser.add_argument("--sensors", type=str, required=True,
                        help="Path to csv file with sensors information")
    parser.add_argument("--include-countries",
                        dest="include_countries",
                        nargs="+",
                        type=str,
                        default=[],
                        help="List of alpha 3 country codes from which include sensors. "
                             "See https://www.iban.com/country-codes for more information")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download forecast for sensors list")
    parser.add_argument("--download-path", type=str, dest="download_path", required=True,
                        help="Path where to put downloaded data")
    parser.add_argument("--s3-uri", type=str, dest="s3_uri", required=False, default=None,
                        help="S3 URI to upload data")
    parser.add_argument("--process-num", type=int, dest="process_num", default=64,
                        help="Number of processes")
    parser.add_argument("--days", type=int, dest="days_num", default=argparse.SUPPRESS, required=False,
                        help="Number of days to download data")
    parser.add_argument("--download-period", type=int, dest="download_period", default=DOWNLOAD_PERIOD, required=False,
                        help="Download period in seconds")
    parser.add_argument("--download-delay", type=int, dest="download_delay", default=0, required=False,
                        help="Download delay in seconds")
    parser.add_argument("--keep-local-snapshots", dest="keep_local_snapshots", action="store_true", required=False,
                        help="Keep local snapshots after upload to S3")

    subparser = parser.add_subparsers(dest="provider", help="Available intergrations")

    # WeatherKit
    wk_parser = subparser.add_parser("wk", help="WeatherKit")
    _add_sensors_params(wk_parser)
    wk_parser.add_argument("--token", type=str, required=True,
                           help="Path to the token configuration file")
    wk_parser.add_argument("--forecast-type", type=str, dest="forecast_type", default="hour", choices=WK_FORECAST_TYPES,
                           help=f"Forecast type. One value of {WK_FORECAST_TYPES}")

    wk_parser.set_defaults(func=_create_wk)

    # AccuWeather
    accu_parser = subparser.add_parser("accuweather", help="AccuWeather")
    _add_sensors_params(accu_parser)
    accu_parser.add_argument("--token", type=str, required=True,
                             help="Token to access AccuWeather API")

    accu_parser.set_defaults(func=_create_accuweather)

    # MyRadar
    myradar_parser = subparser.add_parser("myradar", help="myRadar")
    _add_sensors_params(myradar_parser)
    myradar_parser.add_argument("--key", type=str, required=True,
                                help="Subscirption key")

    myradar_parser.set_defaults(func=_create_myradar)

    # Microsoft
    microsoft_parser = subparser.add_parser(
        "microsoft",
        help="Microsoft (https://learn.microsoft.com/en-us/rest/api/maps/weather/get-minute-forecast?view=rest-maps-2023-06-01&tabs=HTTP)")
    _add_sensors_params(microsoft_parser)
    microsoft_parser.add_argument("--client-id", type=str, dest="client_id", required=True,
                                  help="Client ID")
    microsoft_parser.add_argument("--subscription-key", type=str, dest="subscription_key", required=True,
                                  help="Subscription key")

    microsoft_parser.set_defaults(func=_create_microsoft)

    # Tomorrow IO
    tomorrowio_parser = subparser.add_parser("tomorrowio", help="Tomorrow IO")
    _add_sensors_params(tomorrowio_parser)
    tomorrowio_parser.add_argument("--forecast-type", type=str, dest="forecast_type", default="hour",
                                   choices=TOMORROW_FORECAST_TYPES,
                                   help=f"Forecast type. One value of {TOMORROW_FORECAST_TYPES}")

    tomorrowio_parser.add_argument("--token", type=str, required=True,
                                   help="Token to access Tomorrow IO API")
    tomorrowio_parser.set_defaults(func=_create_tomorrowio)

    # Vaisala
    vaisala_parser = subparser.add_parser("vaisala", help="Vaisala XWeather")
    _add_sensors_params(vaisala_parser)
    vaisala_parser.add_argument("--client-id", type=str, dest="client_id", required=True, help="Client ID")
    vaisala_parser.add_argument("--client-secret", type=str, dest="client_secret", required=True, help="Client Secret")

    vaisala_parser.set_defaults(func=_create_viasala)

    # Open Weather
    openweather_parser = subparser.add_parser(
        "openweather", help="Open Weather")
    _add_sensors_params(openweather_parser)
    openweather_parser.add_argument("--token", type=str, required=True,
                                    help="Token to access Open Weather API")
    openweather_parser.set_defaults(func=_create_open_weather)

    # RainViewer
    rainviewer_parser = subparser.add_parser("rainviewer", help="RainViewer")
    rainviewer_parser.add_argument("--token", type=str, required=True, help="Token to access RainViewer API")
    rainviewer_parser.add_argument("--zoom", type=int, required=False, default=7, help="Zoom level")
    rainviewer_parser.set_defaults(func=_create_rainviewer)

    # Rainbow
    rainbow_parser = subparser.add_parser("rainbow", help="Rainbow")
    _add_sensors_params(rainbow_parser)
    rainbow_parser.add_argument("--token", type=str, required=True, help="Token to access Rainbow API")
    rainbow_parser.set_defaults(func=_create_rainbow)

    # WeatherCompany
    weathercompany_parser = subparser.add_parser("weathercompany", help="WeatherCompany")
    _add_sensors_params(weathercompany_parser)
    weathercompany_parser.add_argument("--token", type=str, required=True, help="Token")
    weathercompany_parser.set_defaults(func=_create_weathercompany)

    args = parser.parse_args()

    forecast_downloader = ForecastDownloader(download_path=args.download_path,
                                             s3_uri=args.s3_uri,
                                             process_num=args.process_num,
                                             download_period=args.download_period,
                                             client_initializer=lambda: args.func(args),
                                             keep_local_snapshots=args.keep_local_snapshots)

    snapshots_to_download = None
    if "days_num" in args:
        snapshots_to_download = args.days_num * 24

    asyncio.run(forecast_downloader.run(snapshots_to_download=snapshots_to_download))
