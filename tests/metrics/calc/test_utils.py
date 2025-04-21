import pandas
import pytest

from metrics.calc.utils import read_selected_sensors

from unittest.mock import patch


class TestCalcUtils:
    @pytest.mark.parametrize("file_path, exp_type", [
        ("1.csv", "csv"),
        ("2.parquet", "parquet"),
        ("3.zip", "zip")
    ])
    @patch("metrics.calc.utils.pandas.read_csv")
    @patch("metrics.calc.utils.pandas.read_parquet")
    def test_read_selected_sensors_file(self,
                                        read_parquet_mock,
                                        read_csv_mock,
                                        file_path: str,
                                        exp_type: str):
        data_type = None

        def _read(path, compression=None):
            nonlocal data_type
            if path.endswith("csv"):
                data_type = "csv"

            if compression == "zip":
                data_type = "zip"

            if path.endswith("parquet"):
                data_type = "parquet"

            return None

        read_parquet_mock.side_effect = _read
        read_csv_mock.side_effect = _read

        read_selected_sensors(path=file_path)

        assert data_type == exp_type

    def test_read_selected_sensors_wrong(self):
        data = read_selected_sensors(None)
        assert all(data.columns == ["id", "lon", "lat", "count", "country"])

        data = read_selected_sensors("test.abcde")
        assert all(data.columns == ["id", "lon", "lat", "count", "country"])

    @patch("metrics.calc.utils.pandas.read_csv")
    @patch("metrics.calc.utils.pandas.read_parquet")
    @patch("metrics.calc.utils.os.listdir")
    @patch("metrics.calc.utils.os.path.isdir")
    def test_read_selected_sensors_dir(self, is_dir_mock, listdir_mock, read_csv_mock, read_parquet_mock):
        data_types = []

        def _read(path, compression=None):
            nonlocal data_types
            if path.endswith("zip"):
                data_types.append("zip")
            elif path.endswith("csv"):
                data_types.append("csv")
            elif path.endswith("parquet"):
                data_types.append("parquet")

            return pandas.DataFrame()

        is_dir_mock.side_effect = [True, False, False, False]

        read_parquet_mock.side_effect = _read
        read_csv_mock.side_effect = _read

        listdir_mock.side_effect = [["1.csv", "2.zip", "3.parquet"]]

        read_selected_sensors("test_dir")

        assert data_types == ["csv", "zip", "parquet"]
