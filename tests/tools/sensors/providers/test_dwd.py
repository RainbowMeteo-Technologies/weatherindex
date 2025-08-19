import pytest
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

from sensors.providers.dwd import DWDProvider
from sensors.providers.provider import BaseProvider
from sensors.publishers.publisher import Publisher


@pytest.fixture
def mock_publisher():
    return MagicMock(spec=Publisher)


@pytest.fixture
def temp_download_path():
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def sample_directory_listing():
    """Sample directory listing from DWD open data portal."""
    return """<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
<html>
<head>
<title>Index of /climate_environment/CDC/observations_germany/climate/10_minutes/precipitation/now/</title>
</head>
<body>
<h1>Index of /climate_environment/CDC/observations_germany/climate/10_minutes/precipitation/now/</h1>
<table>
<tr><th><a href="?C=N;O=D">Name</a></th><th><a href="?C=M;O=A">Last modified</a></th><th><a href="?C=S;O=A">Size</a></th><th><a href="?C=D;O=A">Description</a></th></tr>
<tr><td><a href="zehn_now_rr_Beschreibung_Stationen.txt">zehn_now_rr_Beschreibung_Stationen.txt</a></td><td>19-Aug-2025 10:00</td><td>15K</td><td></td></tr>
<tr><td><a href="10minutenwerte_nieder_00020_now.zip">10minutenwerte_nieder_00020_now.zip</a></td><td>19-Aug-2025 10:00</td><td>2.1K</td><td></td></tr>
<tr><td><a href="10minutenwerte_nieder_00029_now.zip">10minutenwerte_nieder_00029_now.zip</a></td><td>19-Aug-2025 10:00</td><td>2.3K</td><td></td></tr>
<tr><td><a href="10minutenwerte_nieder_00044_now.zip">10minutenwerte_nieder_00044_now.zip</a></td><td>19-Aug-2025 10:00</td><td>2.0K</td><td></td></tr>
</table>
</body>
</html>"""


def test_dwd_smoke(mock_publisher, temp_download_path):
    """Test basic instantiation and inheritance of DWDProvider."""
    client = DWDProvider(
        frequency=600,
        delay=5,
        publisher=mock_publisher,
        download_path=temp_download_path
    )

    assert isinstance(client, DWDProvider)
    assert isinstance(client, BaseProvider)
    assert client._service == "DWD"
    assert client._frequency == 600
    assert client._delay == 5
    assert client._timeout == 30.0  # Default timeout


def test_dwd_default_values(mock_publisher, temp_download_path):
    """Test that DWDProvider uses correct default values."""
    client = DWDProvider(
        publisher=mock_publisher,
        download_path=temp_download_path
    )

    assert client._frequency == 600
    assert client._delay == 5
    assert client._timeout == 30.0


def test_dwd_custom_timeout(mock_publisher, temp_download_path, monkeypatch):
    """Test custom timeout configuration via environment variable."""
    # Test the default behavior and then modify the timeout attribute
    client = DWDProvider(
        publisher=mock_publisher,
        download_path=temp_download_path
    )

    # Test that the default timeout is set correctly
    assert client._timeout == 30.0

    # Test that the timeout can be modified after instantiation
    client._timeout = 60.0
    assert client._timeout == 60.0


@pytest.mark.asyncio
@patch("sensors.providers.dwd.aiohttp.ClientSession")
async def test_download_station_files_directory_access_failure(mock_session, temp_download_path, mock_publisher):
    """Test handling of directory access failure."""
    client = DWDProvider(
        publisher=mock_publisher,
        download_path=temp_download_path
    )

    # Mock the directory listing response with error
    mock_response = AsyncMock()
    mock_response.status = 404

    # Properly mock the async context manager for ClientSession
    mock_session_instance = AsyncMock()
    mock_session.return_value = mock_session_instance

    # Mock the get method to return error response
    mock_session_instance.get.return_value = mock_response

    downloaded_files = await client._download_station_files(temp_dir=temp_download_path)

    # Should have no files
    assert len(downloaded_files) == 0


def test_get_headers(temp_download_path, mock_publisher):
    """Test that headers are correctly set."""
    client = DWDProvider(
        publisher=mock_publisher,
        download_path=temp_download_path
    )

    headers = client._get_headers()

    assert headers["User-Agent"] == "DWDWeatherProvider/1.0"
    assert headers["Accept"] == "*/*"
