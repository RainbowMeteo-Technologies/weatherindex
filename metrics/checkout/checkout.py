import concurrent.futures
import metrics.checkout.constants as constants
import os
import typing

from metrics.checkout.constants import AGGREGATION_PERIOD
from metrics.checkout.data_source import ForecastSourcesInfo, ObservationSourcesInfo, DataSource
from metrics.data_vendor import DataVendor
from metrics.session import Session
from metrics.utils.s3 import S3Client
from metrics.utils.time import format_time
from metrics.utils.time_measure import TimeMeasure
from rich.console import Console


console = Console()


def _build_snapshot_list(start_time: int, end_time: int, period: int) -> typing.List[int]:
    """Builds list of snapshots based on start/end timestamp and step.
    Result timestamps are aligned to period. For example, it will return [30, 60, 90] for
    start_time = 50, end_time = 80, step = 30.
    Start and end timestamps are included into result snapshots range.

    Parameters
    ----------
    start_time : int
        Start timestamp
    end_time : int
        End timestamp
    period : int
        Snapshots period

    Returns
    -------
    typing.List[int]
        List of snaphot timestamps
    """
    assert start_time >= 0, "Invalid start timestamp"
    assert end_time >= 0 and end_time >= start_time, "End timestamp shopuld be >= 0 and >= start timestamp"
    assert period > 0, "Period should be greate than 0"

    start_time = start_time - (start_time % period)
    if end_time % period != 0:
        end_time += period

    snaphots = []
    while start_time <= end_time:
        snaphots.append(start_time)
        start_time += period

    return snaphots


def _build_s3_download_list(snaphots: typing.List[int], s3_uri: str, rule: str) -> typing.List[str]:
    """Builds a list of files to download from s3
    Paramaters
    ----------
    snapshots : typing.List[int]
        List of snapshots to download
    s3_uri : str
        S3 URI of directory where to find files
    rule : str
        Rule for creating filename from timestamp

    Returns
    -------
    typing.List[str]
        Returns list of s3 uri's
    """
    return list(map(lambda item: os.path.join(s3_uri, rule(item)), snaphots))


def _download_file_impl(args):
    uri, file_path = args
    s3_client = S3Client()
    if not s3_client.download_file(s3_uri=uri, file_path=file_path):
        console.log(f"\n[red]Error:[/red] Wasn't able to download {uri}")


def _download_data(s3_uri: str,
                   download_path: str,
                   start_time: int,
                   end_time: int,
                   period: int,
                   rule: str):
    """Downloads timestamps of sensors data from s3.

    Parameters
    ----------
    data_uri : str
        S3 URI of folder with data on s3
    download_path : str
        Path where to download data
    start_time : int
        Start timestamp of download period
    end_time : int
        End timestamp of download period
    period : int
        Period of stored data
    rule : str
        Rule for creating filename from timestamp
    """
    sensors_timestamps = _build_snapshot_list(
        start_time=start_time,
        end_time=end_time,
        period=period)

    download_uri_list = _build_s3_download_list(
        snaphots=sensors_timestamps,
        s3_uri=s3_uri,
        rule=rule)

    download_jobs = []
    for uri, timestamp in zip(download_uri_list, sensors_timestamps):
        _, file_ext = os.path.splitext(uri)
        file_path = os.path.join(download_path, f"{timestamp}{file_ext}")
        download_jobs.append((uri, file_path))

    tm = TimeMeasure()
    console.log(f"Download data from {s3_uri}...")
    with concurrent.futures.ThreadPoolExecutor() as executor:
        executor.map(_download_file_impl, download_jobs)
    console.log(f"Download from {s3_uri} completed in {tm():.2f} seconds...")


def checkout_forecasts(session: Session, forecasts_sources: typing.List[DataSource]):
    def _download_forecast(vendor: str, s3_uri: str, data_folder: str, rule: str, period: int = 600):
        time = format_time(session.start_time - session.forecast_range)
        console.log(f"[yellow]Download `{vendor}` forecast[/yellow]: [{time}, {format_time(session.end_time)}]")
        os.makedirs(data_folder, exist_ok=True)

        _download_data(s3_uri=s3_uri,
                       download_path=data_folder,
                       start_time=session.start_time - session.forecast_range,
                       end_time=session.end_time,
                       period=period,
                       rule=rule)

    os.makedirs(session.data_folder, exist_ok=True)
    for source in forecasts_sources:
        if source.s3_uri is not None:
            _download_forecast(vendor=source.vendor,
                               s3_uri=source.s3_uri,
                               data_folder=source.data_folder,
                               period=source.period,
                               rule=source.filename_rule)


def checkout_sensors(session: Session, observations_sources: typing.List[DataSource]):
    def _download_sensors(vendor: str,
                          s3_uri: str,
                          data_folder: str,
                          rule: str,
                          period: int = 600):
        time = format_time(session.start_time - AGGREGATION_PERIOD)
        console.log(f"[yellow]Download `{vendor}` sensors data[/yellow]: [{time}, {format_time(session.end_time)}]")
        os.makedirs(data_folder, exist_ok=True)

        _download_data(s3_uri=s3_uri,
                       download_path=data_folder,
                       start_time=session.start_time - AGGREGATION_PERIOD,
                       end_time=session.end_time,
                       period=period,
                       rule=rule)

    os.makedirs(session.data_folder, exist_ok=True)
    for source in observations_sources:
        if source.s3_uri is not None:
            _download_sensors(vendor=source.vendor,
                              s3_uri=source.s3_uri,
                              data_folder=source.data_folder,
                              period=source.period,
                              rule=source.filename_rule)


class CheckoutExecutor:
    def __init__(self,
                 session: Session,
                 observations_info: ObservationSourcesInfo,
                 forecasts_info: ForecastSourcesInfo):
        self._session = session

        self.observations_sources = self.observation_sources_list(observations_info)
        self.forecasts_sources = self.forecast_sources_list(forecasts_info)

    def forecast_sources_list(self, forecasts_info: ForecastSourcesInfo) -> typing.List["DataSource"]:
        return [
            DataSource.create(vendor="weather kit", s3_uri=forecasts_info.s3_uri_wk,
                              data_folder=os.path.join(self._session.data_folder, DataVendor.WeatherKit.value),
                              period=constants.WEATHERKIT_PERIOD),
            DataSource.create(vendor="accuweather", s3_uri=forecasts_info.s3_uri_accuweather,
                              data_folder=os.path.join(self._session.data_folder, DataVendor.AccuWeather.value),
                              period=constants.ACCUWEATHER_PERIOD),
            DataSource.create(vendor="rainviewer", s3_uri=forecasts_info.s3_uri_rainviewer,
                              data_folder=os.path.join(self._session.data_folder, DataVendor.RainViewer.value),
                              period=constants.RAINVIEWER_PERIOD),
            DataSource.create(vendor="tomorrow-io", s3_uri=forecasts_info.s3_uri_tomorrowio,
                              data_folder=os.path.join(self._session.data_folder, DataVendor.TomorrowIo.value),
                              period=constants.TOMORROWIO_PERIOD),
            DataSource.create(vendor="vaisala", s3_uri=forecasts_info.s3_uri_vaisala,
                              data_folder=os.path.join(self._session.data_folder, DataVendor.Vaisala.value),
                              period=constants.VAISALA_PERIOD),
            DataSource.create(vendor="rainbowai", s3_uri=forecasts_info.s3_uri_rainbowai,
                              data_folder=os.path.join(self._session.data_folder, DataVendor.RainbowAi.value),
                              period=constants.RAINBOWAI_PERIOD),
            DataSource.create(vendor="weathercompany", s3_uri=forecasts_info.s3_uri_weathercompany,
                              data_folder=os.path.join(self._session.data_folder, DataVendor.WeatherCompany.value),
                              period=constants.WEATHERCOMPANY_PERIOD),
        ]

    def observation_sources_list(self, observations_info: ObservationSourcesInfo) -> typing.List["DataSource"]:
        return [
            DataSource.create(vendor="metar", s3_uri=observations_info.s3_uri_metar,
                              data_folder=os.path.join(self._session.data_folder, DataVendor.Metar.value),
                              period=constants.METAR_PERIOD)
        ]

    def run(self):
        # clear snapshots outside of calculation range before download
        # to reduce peak disk usage for long distance forecasts
        deadline_timestamp = self._session.start_time - self._session.forecast_range - 3600
        deadline_timestamp = deadline_timestamp - (deadline_timestamp % 3600)
        self._session.clear_outdated(deadline_timestamp=deadline_timestamp)

        checkout_forecasts(session=self._session,
                           forecasts_sources=self.forecasts_sources)
        checkout_sensors(session=self._session,
                         observations_sources=self.observations_sources)

        self._session.save_meta()


def checkout(start_time: int,
             end_time: int,
             session_path: str,
             session_clear: bool,
             observations_source: ObservationSourcesInfo,
             forecasts_source: ForecastSourcesInfo,
             forecast_range: int = 7800):
    """
    Checkout specified data into session folder
    """
    console.log(f"Create session:\n"
                f"- session_path = {session_path}\n"
                f"- start_time = {start_time} ({format_time(start_time)})\n"
                f"- end-time = {end_time} ({format_time(end_time)})\n"
                f"- forecast_range = {forecast_range}\n"
                f"- session_clear = {session_clear}\n")

    session = Session.create(start_time=start_time,
                             end_time=end_time,
                             session_path=session_path,
                             session_clear=session_clear,
                             forecast_range=forecast_range)

    console.log(f"Run [green]checkout[/green] command:\n"
                f"Forecast sources:\n"
                f"- s3_uri_rainviewer = {forecasts_source.s3_uri_rainviewer}\n"
                f"- s3_uri_wk = {forecasts_source.s3_uri_wk}\n"
                f"- s3_uri_accuweather = {forecasts_source.s3_uri_accuweather}\n"
                f"- s3_uri_tomorrowio = {forecasts_source.s3_uri_tomorrowio}\n"
                f"- s3_uri_vaisala = {forecasts_source.s3_uri_vaisala}\n"
                f"- s3_uri_rainbowai = {forecasts_source.s3_uri_rainbowai}\n"
                f"- s3_uri_weathercompany = {forecasts_source.s3_uri_weathercompany}\n"
                f"Observation sources:\n"
                f"- s3_uri_metar = {observations_source.s3_uri_metar}")

    checkout_executor = CheckoutExecutor(session=session,
                                         forecasts_info=forecasts_source,
                                         observations_info=observations_source,)
    checkout_executor.run()
