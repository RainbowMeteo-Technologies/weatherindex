import dateutil.parser
import json
import datetime

from metrics.parse.base_parser import BaseParser
from metrics.utils.coords import coord_to_tile_pixel, Coordinate
from metrics.utils.precipitation import PrecipitationType

ZOOM_LEVEL = 7
TILE_SIZE = 256


def _convert_precipitation_to_mm(precip_value: float, unit: str = "mm") -> float:
    """Converts precipitation values to millimeters

    Parameters
    ----------
    precip_value : float
        Precipitation value
    unit : str
        Unit of the precipitation value (e.g., "mm", "inches", "cm")

    Returns
    -------
    float
        Value in millimeters
    """
    if unit.lower() == "mm":
        return precip_value
    elif unit.lower() == "inches":
        return 25.4 * precip_value
    elif unit.lower() == "cm":
        return precip_value * 10
    else:
        # Default to mm if unit is not recognized
        return precip_value


def _parse_timestamp(date_time: str) -> int:
    """Parses string representation of date time into utc timestamp

    This function ensures that the original timestamp is treated as UTC,
    matching the metar parser's behavior.

    Parameters
    ----------
    date_time : str
        String that represents date and time. Examples:
        - ISO format: "2025-08-07T10:00+00:00" (with timezone)
        - ISO format: "2025-08-07T10:00:00Z" (with Z suffix)
        - Standard format: "2025-08-07 10:00:00"

    Returns
    -------
    int
        Returns UTC timestamp in seconds
    """
    try:
        # First try to parse as ISO format with explicit timezone handling
        if date_time.endswith("Z"):
            # Handle Z suffix (UTC) - strip Z and treat as UTC
            date_time_obj = datetime.datetime.fromisoformat(date_time.rstrip("Z")).replace(tzinfo=datetime.timezone.utc)
        elif "+" in date_time and ":" in date_time.split("+")[1]:
            # Handle explicit timezone offset like "+00:00"
            date_time_obj = datetime.datetime.fromisoformat(date_time)
        else:
            # Try ISO format first, then standard format
            try:
                date_time_obj = dateutil.parser.isoparse(date_time)
            except ValueError:
                date_time_obj = dateutil.parser.parse(date_time)

            # If no timezone info, assume UTC (matching metar behavior)
            if date_time_obj.tzinfo is None:
                date_time_obj = date_time_obj.replace(tzinfo=datetime.timezone.utc)

        return int(date_time_obj.timestamp())

    except Exception as e:
        # Fallback: try to parse and assume UTC if no timezone info
        try:
            date_time_obj = dateutil.parser.parse(date_time)
            if date_time_obj.tzinfo is None:
                date_time_obj = date_time_obj.replace(tzinfo=datetime.timezone.utc)
            return int(date_time_obj.timestamp())
        except Exception:
            raise ValueError(f"Could not parse timestamp: {date_time}")


class AustriaParser(BaseParser):
    """
    Parser for Austria Geosphere API-based observation service.

    This parser handles GeoJSON data from the Austria weather API and extracts
    precipitation observations for various locations, matching the metar format.

    EXPECTED JSON FORMAT:
    The provider returns JSON data in this format:

    {
        "timestamp": 1234567890,
        "observations": [
            {
                "id": "11044",
                "lat": 48.221111111111114,
                "lon": 16.26527777777778,
                "timestamp": "2025-08-07T10:00+00:00",
                "precipitation": 2.5,
                "unit": "mm"
            },
            ...
        ]
    }

    REQUIRED FIELDS:
    - timestamp: ISO format or standard datetime string
    - id: Unique identifier for the location/station
    - lat: Latitude coordinate
    - lon: Longitude coordinate
    - precipitation: Precipitation value

    OPTIONAL FIELDS:
    - unit: Unit of precipitation (defaults to "mm")
    """

    def _parse_impl(self, timestamp: int, file_name: str, data: bytes) -> list:
        """
        Parse the JSON data from the Austria API response.

        Parameters
        ----------
        timestamp : int
            Expected timestamp for this data
        file_name : str
            Name of the file being parsed
        data : bytes
            Raw JSON data from the Austria API response

        Returns
        -------
        list
            List of rows with the following format:
            [sensor_id, lon, lat, timestamp, precip_rate, precip_type, px, py, tile_x, tile_y]
        """
        rows = []

        try:
            # Parse JSON data
            json_data = json.loads(data.decode("utf-8"))

            # Extract observations from the JSON data
            observations = self._extract_observations(json_data)

            for obs in observations:
                # Extract required fields
                sensor_id = f"austria_{obs["id"]}"  # Prefix with service name
                lat = obs["lat"]
                lon = obs["lon"]
                obs_timestamp = _parse_timestamp(obs["timestamp"])
                precip_rate = _convert_precipitation_to_mm(obs["precipitation"], obs.get("unit", "mm"))

                # Skip null/missing precipitation data, but include 0.0 (no rain)
                if precip_rate is None:
                    continue

                # Convert coordinates to tile pixels
                pixel = coord_to_tile_pixel(coord=Coordinate(lon=lon, lat=lat),
                                            zoom_level=ZOOM_LEVEL,
                                            tile_size=TILE_SIZE)

                # Add row in the required format (matching metar exactly)
                rows.append((
                    sensor_id, lon, lat, obs_timestamp, precip_rate,
                    PrecipitationType.RAIN.value,  # Austria provides rainfall data
                    pixel.px, pixel.py, pixel.tile_x, pixel.tile_y
                ))

        except Exception as e:
            # Log parsing errors but don't fail completely
            print(f"Error parsing {file_name}: {e}")

        return rows

    def _extract_observations(self, json_data: dict) -> list:
        """
        Extract observations from the Austria API JSON data structure.

        This method handles the specific format returned by the Austria Geosphere API
        and extracts the required fields for each observation.

        Parameters
        ----------
        json_data : dict
            The parsed JSON data from the API response

        Returns
        -------
        list
            List of observation dictionaries, each containing:
            - id: station identifier
            - lat: latitude
            - lon: longitude
            - timestamp: timestamp string
            - precipitation: precipitation value
            - unit: unit of precipitation (optional, defaults to "mm")
        """
        observations = []

        # Extract observations array from the processed data
        if "observations" in json_data:
            for obs in json_data["observations"]:
                # Validate required fields
                if all(key in obs for key in ["id", "lat", "lon", "timestamp", "precipitation"]):
                    observations.append({
                        "id": obs["id"],
                        "lat": obs["lat"],
                        "lon": obs["lon"],
                        "timestamp": obs["timestamp"],
                        "precipitation": obs["precipitation"],
                        "unit": obs.get("unit", "mm")
                    })

        return observations

    def _should_parse_file_extension(self, file_extension: str) -> bool:
        """Check if this parser should handle files with this extension"""
        return file_extension == ".json"

    def _get_columns(self) -> list:
        """Return the column names for the parsed data (matching metar format)"""
        return ["id", "lon", "lat", "timestamp", "precip_rate", "precip_type", "px", "py", "tile_x", "tile_y"]
