from enum import Enum

from metrics.parse.parse import ParseSource, _process_source, parse
from metrics.data_vendor import BaseDataVendor, DataVendor
from metrics.parse.base_parser import BaseParser

from unittest.mock import MagicMock, patch


class UnsupportedVendor(BaseDataVendor, Enum):
    WeatherTest = "weather-test"


class PickableMockParser(BaseParser):
    def parse(input_archive_path: str, output_parquet_path: str):
        pass


class TestParse:
    @patch("metrics.parse.parse.Session.create_from_folder")
    @patch("metrics.parse.parse._process_source")
    @patch("metrics.parse.parse.os.makedirs")
    def test_parse_smoke(self, mkdir_mock, process_source_mock: MagicMock, create_session_mock):
        parse(session_path="test",
              process_num=1,
              providers=[DataVendor.AccuWeather,
                         DataVendor.Vaisala,
                         UnsupportedVendor.WeatherTest])

        processed_sources = []
        for args, kwargs in process_source_mock.call_args_list:
            processed_sources.append(kwargs["source"].vendor)

        assert processed_sources == [DataVendor.AccuWeather.name, DataVendor.Vaisala.name]

    @patch("metrics.parse.parse._execute_source_jobs")
    @patch("metrics.parse.parse.os.walk")
    @patch("metrics.parse.parse.os.makedirs")
    def test_process_source_smoke(self, os_mkdir_mock, os_walk_mock, exec_mock: MagicMock):
        source = None
        process_num = 1

        os_walk_mock.return_value = [("test/", (), ("1.zip",))]

        source = ParseSource(vendor="test",
                             input_folder="test",
                             output_folder="test",
                             parser_class=PickableMockParser)

        _process_source(source=source, process_num=process_num)

        args, kwargs = exec_mock.call_args

        assert kwargs["source_name"] == "test"
        assert kwargs["process_num"] == 1
        assert kwargs["jobs"][0].input_archive_path == "test/1.zip"
