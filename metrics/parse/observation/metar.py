import datetime
import typing
import xml.etree.ElementTree as xml

from enum import IntEnum

from metar import Metar
from metrics.parse.base_parser import BaseParser
from metrics.utils.coords import Coordinate, coord_to_tile_pixel
from rich.console import Console
from metrics.utils.precipitation import PrecipitationType

ZOOM_LEVEL = 7
TILE_SIZE = 256
DEFAULT_PRECIP_RATE = 10.0

console = Console()


def to_date(timestamp: int) -> datetime.datetime:
    return datetime.datetime.fromtimestamp(timestamp, datetime.UTC)


CLOUD_BASE_UNDEFINED = 0


class SkyCover(IntEnum):
    """
    An enumeration representing cloud coverage levels in aviation weather reports (METAR/TAF).
    Values are ordered from least (0 = clear) to maximum coverage (7 = fully obscured).

    The height of cloud base shall be reported in steps of 30 m (100 ft) up to 3 000 m (10 000
    ft). Any observed value which does not fit the reporting scale in use shall be rounded
    down to the nearest lower step in the scale.

    Quick start:
    - https://groundschool.weebly.com/uploads/2/3/6/7/2367787/25_analyzing_weather_data.pdf
    - https://library.wmo.int/records/item/35713-manual-on-codes-volume-i-1-international-codes (Volume I.1 A-33)
    """
    SKC = 0       # Sky Clear (no clouds, manual observation)
    CLR = 1       # Clear (no clouds below 12,000 ft, automated)
    CAVOK = 2     # Ceiling and Visibility OK (implies no significant clouds)
    FEW = 3       # Few clouds (1/8 to 2/8 coverage)
    SCT = 4       # Scattered (3/8 to 4/8 coverage)
    BKN = 5       # Broken (5/8 to 7/8 coverage)
    OVC = 6       # Overcast (8/8 coverage, fully covered)
    OVX = 7       # Obscured (sky hidden, treated as fully covered)


class MetarParser(BaseParser):

    def _parse_impl(self, timestamp: int, file_name: str, data: bytes) -> typing.List[typing.List[any]]:
        """See :func:`~metrics.base_parser.BaseParser._parse_impl`"""

        # Weather codes taken from here: https://www.weather.gov/media/wrh/mesowest/metar_decode_key.pdf
        def _is_rain(codes: str) -> bool:
            has_rain = False

            # low drizzle
            if "-" in codes and "DZ" in codes:
                return has_rain

            rain_codes = ["DZ", "RA", "GR"]
            for code in codes:
                has_rain = has_rain or (code in rain_codes)

            return has_rain

        def _is_snow(codes: str) -> bool:
            has_snow = False

            snow_codes = ["SN", "GS", "SG", "SNINCR", "SP", "SW", "S"]
            for code in codes:
                has_snow = has_snow or (code in snow_codes)

            return has_snow

        def _should_skip_report(report: str) -> bool:
            skip_criteria = ["RAB" in report,       # report with time offset
                             report.endswith("$")]  # sensor is on maintenance

            return any(skip_criteria)

        def _sky_condition(child: xml.Element) -> tuple:
            record = []

            for item in child.findall("sky_condition"):
                sky_cover = item.get("sky_cover")
                if sky_cover in SkyCover.__members__:
                    cloud_base_ft_agl = int(item.get("cloud_base_ft_agl", CLOUD_BASE_UNDEFINED))
                    record.append((SkyCover[sky_cover].value, cloud_base_ft_agl))

            return record

        report_date = to_date(timestamp)

        rows = []
        # Load and parse the XML file
        try:
            tree = xml.fromstring(data)
            for child in tree.iter("METAR"):

                try:
                    raw_text = child.find("raw_text")
                    if raw_text is None:
                        continue

                    if _should_skip_report(raw_text.text):
                        continue

                    metar = Metar.Metar(raw_text.text, month=report_date.month, year=report_date.year)

                    lon = float(child.find("longitude").text)
                    lat = float(child.find("latitude").text)
                    id = child.find("station_id").text
                    obs_timestamp = self._parse_timestamp(child.find("observation_time").text)
                    sky_condition = _sky_condition(child)

                    # check valid coordinates
                    if not Coordinate(lon=lon, lat=lat).is_valid():
                        continue

                except Metar.ParserError as ex:
                    # console.log(f"Metar.ParserError while parsing file {file_name}: {ex}")
                    continue
                except AttributeError as ex:
                    # console.log(f"AttributeError while parsing file {file_name}: {ex}")
                    continue

                has_rain = any(_is_rain(code) for code in metar.weather)
                has_snow = any(_is_snow(code) for code in metar.weather)

                pixel = coord_to_tile_pixel(coord=Coordinate(lon=lon, lat=lat),
                                            zoom_level=ZOOM_LEVEL,
                                            tile_size=TILE_SIZE)

                precip_type = PrecipitationType.UNKNOWN.value
                precip_rate = 0.0
                if has_rain or has_snow:
                    precip_rate = DEFAULT_PRECIP_RATE

                if has_rain and has_snow:
                    precip_type = PrecipitationType.MIX.value
                elif has_rain:
                    precip_type = PrecipitationType.RAIN.value
                elif has_snow:
                    precip_type = PrecipitationType.SNOW.value

                rows.append([id, lon, lat, obs_timestamp, precip_rate,
                             precip_type, pixel.px, pixel.py,
                             pixel.tile_x, pixel.tile_y, sky_condition])

        except xml.ParseError as ex:
            console.log(f"xml.ParseError while parsing file {file_name}: {ex}")

        return rows

    def _should_parse_file_extension(self, file_extension: str) -> bool:
        """See :func:`~metrics.base_parser.BaseParser._should_parse_file_extension`"""
        return file_extension == ".xml"

    def _get_columns(self) -> typing.List[str]:
        """See :func:`~metrics.base_parser.BaseParser._get_columns`"""
        return ["id", "lon", "lat", "timestamp", "precip_rate", "precip_type", "px", "py",
                "tile_x", "tile_y", "sky_condition"]

    def _parse_timestamp(self, time_str: str) -> int:
        """Parses timestamp from a string"""
        date = datetime.datetime.fromisoformat(time_str.rstrip("Z")).replace(tzinfo=datetime.timezone.utc)
        return int(date.timestamp())
