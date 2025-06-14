import argparse
import asyncio

from forecast.providers.accuweather import AccuWeather
from forecast.providers.microsoft import Microsoft
from forecast.providers.myradar import MyRadar
from forecast.providers.openweather import OpenWeather
from forecast.providers.rainbow import Rainbow
from forecast.providers.rainviewer import RainViewer
from forecast.providers.tomorrowio import TomorrowIo, TOMORROW_FORECAST_TYPES
from forecast.providers.vaisala import Vaisala
from forecast.providers.weather_company import WeatherCompany
from forecast.providers.weather_kit import WeatherKit, WK_FORECAST_TYPES

from forecast.sensor import Sensor
from rich.console import Console

from forecast.publishers.publisher import Publisher, NullPublisher
from forecast.publishers.s3 import S3Publisher
from forecast.providers.provider import BaseProvider


console = Console()


def _create_publisher(args: argparse.Namespace) -> Publisher:
    if args.s3_uri is not None:
        return S3Publisher(args.s3_uri)
    else:
        return NullPublisher()


def _create_wk(args: argparse.Namespace) -> WeatherKit:
    publisher = _create_publisher(args)
    sensors = Sensor.from_csv(sensors_path=args.sensors,
                              include_countries=args.include_countries)

    return WeatherKit(download_path=args.download_path,
                      publisher=publisher,
                      process_num=args.process_num,
                      chunk_size=args.chunk_size,
                      frequency=args.download_period,
                      config_path=args.config_path,
                      forecast_type=args.forecast_type,
                      sensors=sensors)


def _create_accuweather(args: argparse.Namespace) -> AccuWeather:
    publisher = _create_publisher(args)
    sensors = Sensor.from_csv(sensors_path=args.sensors,
                              include_countries=args.include_countries)

    return AccuWeather(download_path=args.download_path,
                       publisher=publisher,
                       process_num=args.process_num,
                       chunk_size=args.chunk_size,
                       frequency=args.download_period,
                       token=args.token,
                       sensors=sensors)


def _create_myradar(args: argparse.Namespace) -> MyRadar:
    publisher = _create_publisher(args)
    sensors = Sensor.from_csv(sensors_path=args.sensors,
                              include_countries=args.include_countries)

    return MyRadar(download_path=args.download_path,
                   publisher=publisher,
                   process_num=args.process_num,
                   chunk_size=args.chunk_size,
                   frequency=args.download_period,
                   sub_key=args.key,
                   sensors=sensors)


def _create_microsoft(args: argparse.Namespace) -> Microsoft:
    publisher = _create_publisher(args)
    sensors = Sensor.from_csv(sensors_path=args.sensors,
                              include_countries=args.include_countries)

    return Microsoft(download_path=args.download_path,
                     publisher=publisher,
                     process_num=args.process_num,
                     chunk_size=args.chunk_size,
                     frequency=args.download_period,
                     cliend_id=args.client_id,
                     subscription_key=args.subscription_key,
                     sensors=sensors)


def _create_tomorrowio(args: argparse.Namespace) -> TomorrowIo:
    publisher = _create_publisher(args)
    sensors = Sensor.from_csv(sensors_path=args.sensors,
                              include_countries=args.include_countries)

    return TomorrowIo(download_path=args.download_path,
                      publisher=publisher,
                      process_num=args.process_num,
                      chunk_size=args.chunk_size,
                      frequency=args.download_period,
                      token=args.token,
                      forecast_type=args.forecast_type,
                      sensors=sensors)


def _create_viasala(args: argparse.Namespace) -> Vaisala:
    publisher = _create_publisher(args)
    sensors = Sensor.from_csv(sensors_path=args.sensors,
                              include_countries=args.include_countries)

    return Vaisala(download_path=args.download_path,
                   publisher=publisher,
                   process_num=args.process_num,
                   chunk_size=args.chunk_size,
                   frequency=args.download_period,
                   client_id=args.client_id,
                   client_secret=args.client_secret,
                   sensors=sensors)


def _create_open_weather(args: argparse.Namespace) -> OpenWeather:
    publisher = _create_publisher(args)
    sensors = Sensor.from_csv(sensors_path=args.sensors,
                              include_countries=args.include_countries)

    return OpenWeather(download_path=args.download_path,
                       publisher=publisher,
                       process_num=args.process_num,
                       chunk_size=args.chunk_size,
                       frequency=args.download_period,
                       token=args.token,
                       sensors=sensors)


def _create_rainbow(args: argparse.Namespace) -> Rainbow:
    publisher = _create_publisher(args)
    sensors = Sensor.from_csv(sensors_path=args.sensors,
                              include_countries=args.include_countries)

    return Rainbow(download_path=args.download_path,
                   publisher=publisher,
                   process_num=args.process_num,
                   chunk_size=args.chunk_size,
                   frequency=args.download_period,
                   token=args.token,
                   sensors=sensors)


def _create_rainviewer(args: argparse.Namespace) -> RainViewer:
    publisher = _create_publisher(args)

    return RainViewer(download_path=args.download_path,
                      publisher=publisher,
                      process_num=args.process_num,
                      chunk_size=args.chunk_size,
                      frequency=args.download_period,
                      token=args.token, zoom=args.zoom)


def _create_weathercompany(args: argparse.Namespace) -> WeatherCompany:
    publisher = _create_publisher(args)
    sensors = Sensor.from_csv(sensors_path=args.sensors,
                              include_countries=args.include_countries)

    return WeatherCompany(download_path=args.download_path,
                          publisher=publisher,
                          process_num=args.process_num,
                          chunk_size=args.chunk_size,
                          frequency=args.download_period,
                          sensors=sensors,
                          token=args.token)


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

    # Storage and publish destination
    parser.add_argument("--download-path", type=str, dest="download_path", required=True,
                        help="Path where to put downloaded data")
    parser.add_argument("--s3-uri", type=str, dest="s3_uri", required=False, default=None,
                        help="S3 URI to upload data")

    # Download timing
    parser.add_argument("--download-period", type=int, dest="download_period", default=600, required=False,
                        help="Download period in seconds")
    parser.add_argument("--download-delay", type=int, dest="download_delay", default=0, required=False,
                        help="Download delay in seconds")

    # Parallel execution
    parser.add_argument("--process-num", type=int, dest="process_num", default=None, required=False,
                        help="Number of processes")
    parser.add_argument("--chunk-size", type=int, dest="chunk_size", default=None, required=False,
                        help="Chunk size")

    subparser = parser.add_subparsers(dest="provider", help="Available intergrations")

    # WeatherKit
    wk_parser = subparser.add_parser("wk", help="WeatherKit")
    _add_sensors_params(wk_parser)
    wk_parser.add_argument("--config-path", type=str, required=True,
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
                                help="Subscription key")

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
    openweather_parser = subparser.add_parser("openweather", help="Open Weather")
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

    provider: BaseProvider = args.func(args)

    asyncio.run(provider.run())
