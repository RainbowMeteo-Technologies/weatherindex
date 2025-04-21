import json
import os
import re

from metrics.utils.time import format_time
from rich.console import Console

console = Console()

# sensors
SENSORS_FOLDER = "sensors"

# data
DATA_FOLDER = "data"

# parse
TABLES_FOLDER = "tables"

# metrics
METRICS_FOLDER = "metrics"


class Session:

    def __init__(self,
                 session_path: str,
                 start_time: int,
                 end_time: int,
                 forecast_range: int = 7800,
                 data_folder: str = None,
                 sensors_folder: str = None,
                 tables_folder: str = None,
                 metrics_folder: str = None):
        self._path = session_path
        self._start_time = start_time
        self._end_time = end_time
        self._forecast_range = forecast_range
        self._data_folder = data_folder or os.path.join(self._path, DATA_FOLDER)
        self._tables_folder = tables_folder or os.path.join(self._path, TABLES_FOLDER)
        self._sensors_folder = sensors_folder or os.path.join(self._path, SENSORS_FOLDER)
        self._metrics_folder = metrics_folder or os.path.join(self._path, METRICS_FOLDER)

    @property
    def session_name(self) -> str:
        return os.path.basename(self._path)

    @property
    def start_time(self) -> int:
        return self._start_time

    @property
    def end_time(self) -> int:
        return self._end_time

    @property
    def forecast_range(self) -> int:
        return self._forecast_range

    @property
    def data_folder(self) -> str:
        return self._data_folder

    @property
    def sensors_folder(self) -> str:
        return self._sensors_folder

    @property
    def tables_folder(self) -> str:
        return self._tables_folder

    @property
    def metrics_folder(self) -> str:
        return self._metrics_folder

    def __repr__(self) -> str:
        return (f"Session {self._path}:\n"
                f"- start_time: {self._start_time} ({format_time(self._start_time)})\n"
                f"- end_time: {self._end_time} ({format_time(self._end_time)})\n"
                f"- forecast_range: {self._forecast_range}\n"
                f"- data_folder: {self.data_folder}\n"
                f"- sensors_folder: {self.sensors_folder}\n"
                f"- tables_folder: {self.tables_folder}\n"
                f"- metrics_folder: {self.metrics_folder}\n")

    def save_meta(self):
        """Saves meta info for the session
        """
        with open(os.path.join(self._path, "meta.json"), "w") as file:
            file.write(json.dumps({
                "start_time": self._start_time,
                "end_time": self._end_time,
                "forecast_range": self._forecast_range,
                "data_folder": self.data_folder,
                "sensors_folder": self.sensors_folder,
                "tables_folder": self.tables_folder,
                "metrics_folder": self.metrics_folder
            }, indent=4))

    @staticmethod
    def create_from_folder(session_path: str) -> "Session":
        """Creates Session object from folder path

        Parameters
        ----------
        session_path : str
            Folder path of a session
        """
        with open(os.path.join(session_path, "meta.json"), "r") as file:
            meta = json.loads(file.read())

        session = Session(session_path=session_path,
                          start_time=meta["start_time"],
                          end_time=meta["end_time"],
                          forecast_range=meta["forecast_range"],
                          data_folder=meta["data_folder"],
                          sensors_folder=meta["sensors_folder"],
                          tables_folder=meta["tables_folder"],
                          metrics_folder=meta["metrics_folder"])

        return session

    def _clear_outdated(self, target_dir: str, deadline: int):
        timestamp_regexp = r'^\d+(?=\.(zip|gz|parquet|csv)$)'
        for dir, _, files in os.walk(target_dir):
            for file_name in files:
                match = re.match(timestamp_regexp, file_name)
                if match:
                    timestamp = int(match.group())
                    if timestamp < deadline:
                        os.remove(os.path.join(dir, file_name))

    def clear_outdated(self, deadline_timestamp: int):
        console.log(f"Clear data older then {deadline_timestamp} ({format_time(deadline_timestamp)})")
        target_dirs = [self.data_folder,
                       self.sensors_folder,
                       self.tables_folder]

        for dir in target_dirs:
            self._clear_outdated(target_dir=dir, deadline=deadline_timestamp)
