import datetime
import pytest
import typing

from metrics.parse.observation.metar import CLOUD_BASE_UNDEFINED, MetarParser, SkyCover
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
                       wind_speed_kt: float = 23.0,
                       sky_condition: typing.List[str] = []) -> str:

    sky_condition_str = "\n".join(sky_condition)

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
      {sky_condition_str}
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
        # clear sky without sky condition reporting
        (
            _create_metar_file(raw_text="TJBQ 251150Z 00000KT 10SM 25/21 A2990",
                               station_id="TJBQ",
                               observation_time="2024-03-25T11:50:00Z",
                               lat=18.494,
                               lon=-67.128,
                               temp_c=25.4,
                               dew_point=21,
                               wind_dir_degrees=5.4,
                               wind_speed_kt=23.0,
                               sky_condition=[]),
            1725663600,

            # ["id", "lon", "lat", "timestamp", "precip_rate", "precip_type", "px", "py", "tile_x", "tile_y",
            # "sky_condition"]
            [
                ["TJBQ", -67.128, 18.494, 1711367400, 0.0, PrecipitationType.UNKNOWN.value, 33, 78, 40, 57,
                 []]
            ]
        ),
        # clear sky with sky condition reporting
        (
            _create_metar_file(raw_text="TJBQ 251150Z 00000KT 10SM CLR 25/21 A2990",
                               station_id="TJBQ",
                               observation_time="2024-03-25T11:50:00Z",
                               lat=18.494,
                               lon=-67.128,
                               temp_c=25.4,
                               dew_point=21,
                               wind_dir_degrees=5.4,
                               wind_speed_kt=23.0,
                               sky_condition=['<sky_condition sky_cover="CLR"/>']),
            1725663600,

            # ["id", "lon", "lat", "timestamp", "precip_rate", "precip_type", "px", "py", "tile_x", "tile_y",
            # "sky_condition"]
            [
                ["TJBQ", -67.128, 18.494, 1711367400, 0.0, PrecipitationType.UNKNOWN.value, 33, 78, 40, 57,
                 [(SkyCover.CLR, CLOUD_BASE_UNDEFINED)]]
            ]
        ),
        # only rain
        (
            _create_metar_file(raw_text="TJBQ 251150Z 00000KT 10SM RA FEW039 SCT049 BKN060 25/21 A2990",
                               station_id="TJBQ",
                               observation_time="2024-03-25T11:50:00Z",
                               lat=18.494,
                               lon=-67.128,
                               temp_c=25.4,
                               dew_point=21,
                               wind_dir_degrees=5.4,
                               wind_speed_kt=23.0,
                               sky_condition=['<sky_condition sky_cover="FEW" cloud_base_ft_agl="3900" />',
                                              '<sky_condition sky_cover="SCT" cloud_base_ft_agl="4900" />',
                                              '<sky_condition sky_cover="BKN" cloud_base_ft_agl="6000" />']),
            1725667200,

            # ["id", "lon", "lat", "timestamp", "precip_rate", "precip_type", "px", "py", "tile_x", "tile_y",
            # "sky_condition"]
            [
                ["TJBQ", -67.128, 18.494, 1711367400, 10.0, PrecipitationType.RAIN.value, 33, 78, 40, 57,
                 [(SkyCover.FEW.value, 3900), (SkyCover.SCT.value, 4900), (SkyCover.BKN.value, 6000)]]
            ]
        ),
        # only snow
        (
            _create_metar_file(raw_text="TJBQ 251150Z 00000KT 10SM SN OVC020 25/21 A2990",
                               station_id="TJBQ",
                               observation_time="2024-03-25T11:50:00Z",
                               lat=18.494,
                               lon=-67.128,
                               temp_c=25.4,
                               dew_point=21,
                               wind_dir_degrees=5.4,
                               wind_speed_kt=23.0,
                               sky_condition=['<sky_condition sky_cover="OVC" cloud_base_ft_agl="2000" />']),
            1725667200,

            # ["id", "lon", "lat", "timestamp", "precip_rate", "precip_type", "px", "py", "tile_x", "tile_y",
            # "sky_condition"]
            [
                ["TJBQ", -67.128, 18.494, 1711367400, 10.0, PrecipitationType.SNOW.value, 33, 78, 40, 57,
                 [(SkyCover.OVC.value, 2000)]]
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
                               wind_speed_kt=23.0,
                               sky_condition=['<sky_condition sky_cover="SCT" cloud_base_ft_agl="1000" />',
                                              '<sky_condition sky_cover="BKN" cloud_base_ft_agl="1500" />']),
            1725667200,

            # ["id", "lon", "lat", "timestamp", "precip_rate", "precip_type", "px", "py", "tile_x", "tile_y",
            # "sky_condition"]
            [
                ["TJBQ", -67.128, 18.494, 1711367400, 10.0, PrecipitationType.MIX.value, 33, 78, 40, 57,
                 [(SkyCover.SCT.value, 1000), (SkyCover.BKN.value, 1500)]]
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
