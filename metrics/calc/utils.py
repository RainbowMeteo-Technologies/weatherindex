import os
import pandas
import typing


def read_selected_sensors(path: typing.Optional[str] = None) -> pandas.DataFrame:
    """Read path and return list of selected sensor IDs.

    Parameters
    ----------
    path : str
        Path to directory or a file (.csv, .csv.zip or .parquet) where to find data with sensor id's.
        Column "id" is mandatory in data.
    """

    if path is None:
        return pandas.DataFrame(columns=["id", "lon", "lat", "count", "country"])

    if os.path.isdir(path):
        aggregated_sensors_data = []
        for file_name in os.listdir(path):
            file_path = os.path.join(path, file_name)
            aggregated_sensors_data.append(read_selected_sensors(file_path))

        return pandas.concat(aggregated_sensors_data)
    elif path.endswith(".csv"):
        return pandas.read_csv(path)
    elif path.endswith(".parquet"):
        return pandas.read_parquet(path)
    elif path.endswith(".zip"):
        return pandas.read_csv(path, compression="zip")

    return pandas.DataFrame(columns=["id", "lon", "lat", "count", "country"])
