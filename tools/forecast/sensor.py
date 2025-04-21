import pandas

from dataclasses import dataclass
from typing import List


@dataclass
class Sensor:
    id: str
    lon: float
    lat: float
    country: str

    @staticmethod
    def from_csv(sensors_path: str, include_countries: List[str] = []) -> List["Sensor"]:
        sensors = pandas.read_csv(sensors_path)

        if len(include_countries) > 0:
            sensors = sensors[sensors["country"].isin(include_countries)]

        return [Sensor(id=row["id"],
                       lon=row["lon"],
                       lat=row["lat"],
                       country=row["country"]) for _, row in sensors.iterrows()]
