import datetime
import pytest
import typing

from metrics.parse.observation.metar import MetarParser
from metrics.utils.precipitation import PrecipitationType
from unittest.mock import MagicMock, patch


def _create_metar_file(raw_text: str = "TJBQ 251150Z 00000KT 10SM CLR 25/21 A2990",
                       station_id: str = "TJBQ",
                       observation_time: str = "2024-03-25T11:50:00Z",
                       lat: float = 18.494,
                       lon: float = -67.128,
                       temp_c: float = 25.4,
                       dew_point: float = 21,
                       wind_dir_degrees: float = 5.4,
                       wind_speed_kt: float = 23.0) -> str:
    return f'''
<response xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" version="1.3" xsi:noNamespaceSchemaLocation="https://aviationweather.gov/data/schema/metar1_3.xsd">
  <request_index>1711367461</request_index>
  <data_source name="metars" />
  <request type="retrieve" />
  <errors />
  <warnings />
  <time_taken_ms>87</time_taken_ms>
  <data num_results="5093">
    <METAR>
      <raw_text>{raw_text}</raw_text>
      <station_id>{station_id}</station_id>
      <observation_time>{observation_time}</observation_time>
      <latitude>{lat}</latitude>
      <longitude>{lon}</longitude>
      <temp_c>{temp_c}</temp_c>
      <dewpoint_c>{dew_point}</dewpoint_c>
      <wind_dir_degrees>{wind_dir_degrees}</wind_dir_degrees>
      <wind_speed_kt>{wind_speed_kt}</wind_speed_kt>
      <visibility_statute_mi>10+</visibility_statute_mi>
      <altim_in_hg>29.90</altim_in_hg>
      <sky_condition sky_cover="CLR"/>
      <flight_category>VFR</flight_category>
      <metar_type>METAR</metar_type>
      <elevation_m>69</elevation_m>
    </METAR>
  </data>
</response>
'''


class TestMetarParser:

    @pytest.mark.parametrize("time_str, expected_timestamp", [
        ("2024-03-25T11:50:00Z", 1711367400),
        ("2024-03-25T11:47:00Z", 1711367220),
    ])
    def test_parse_timestamp(self,
                             time_str: str,
                             expected_timestamp: int):
        parser = MetarParser()

        assert parser._parse_timestamp(time_str) == expected_timestamp

    @pytest.mark.parametrize("sample_xml, report_timestamp, expected_rows", [
        (
            _create_metar_file(raw_text="TJBQ 251150Z 00000KT 10SM CLR 25/21 A2990",
                               station_id="TJBQ",
                               observation_time="2024-03-25T11:50:00Z",
                               lat=18.494,
                               lon=-67.128,
                               temp_c=25.4,
                               dew_point=21,
                               wind_dir_degrees=5.4,
                               wind_speed_kt=23.0),
            1725663600,

            # ["id", "lon", "lat", "timestamp", "precip_rate", "precip_type", "px", "py", "tile_x", "tile_y"]
            [
                ["TJBQ", -67.128, 18.494, 1711367400, 0.0, PrecipitationType.UNKNOWN.value, 33, 78, 40, 57]
            ]
        ),
        # only rain
        (
            _create_metar_file(raw_text="TJBQ 251150Z 00000KT 10SM RA 25/21 A2990",
                               station_id="TJBQ",
                               observation_time="2024-03-25T11:50:00Z",
                               lat=18.494,
                               lon=-67.128,
                               temp_c=25.4,
                               dew_point=21,
                               wind_dir_degrees=5.4,
                               wind_speed_kt=23.0),
            1725667200,

            # ["id", "lon", "lat", "timestamp", "precip_rate", "precip_type", "px", "py", "tile_x", "tile_y"]
            [
                ["TJBQ", -67.128, 18.494, 1711367400, 10.0, PrecipitationType.RAIN.value, 33, 78, 40, 57]
            ]
        ),
        # only snow
        (
            _create_metar_file(raw_text="TJBQ 251150Z 00000KT 10SM SN 25/21 A2990",
                               station_id="TJBQ",
                               observation_time="2024-03-25T11:50:00Z",
                               lat=18.494,
                               lon=-67.128,
                               temp_c=25.4,
                               dew_point=21,
                               wind_dir_degrees=5.4,
                               wind_speed_kt=23.0),
            1725667200,

            # ["id", "lon", "lat", "timestamp", "precip_rate", "precip_type", "px", "py", "tile_x", "tile_y"]
            [
                ["TJBQ", -67.128, 18.494, 1711367400, 10.0, PrecipitationType.SNOW.value, 33, 78, 40, 57]
            ]
        ),
        # mix
        (
            _create_metar_file(raw_text="TJBQ 251150Z 00000KT 10SM RA SN 25/21 A2990",
                               station_id="TJBQ",
                               observation_time="2024-03-25T11:50:00Z",
                               lat=18.494,
                               lon=-67.128,
                               temp_c=25.4,
                               dew_point=21,
                               wind_dir_degrees=5.4,
                               wind_speed_kt=23.0),
            1725667200,

            # ["id", "lon", "lat", "timestamp", "precip_rate", "precip_type", "px", "py", "tile_x", "tile_y"]
            [
                ["TJBQ", -67.128, 18.494, 1711367400, 10.0, PrecipitationType.MIX.value, 33, 78, 40, 57]
            ]
        )
    ])
    @patch("metrics.parse.observation.metar.to_date")
    def test_parse_impl(self, mock_to_date: MagicMock, sample_xml: str, report_timestamp: int,
                        expected_rows: typing.List[typing.List[any]]):
        parser = MetarParser()
        mock_to_date.return_value = datetime.datetime.fromtimestamp(report_timestamp, datetime.UTC)
        got_rows = parser._parse_impl(
            timestamp=report_timestamp,
            file_name="metar.xml",
            data=sample_xml.encode("utf-8"))

        mock_to_date.assert_called_once_with(report_timestamp)
        assert got_rows == expected_rows
