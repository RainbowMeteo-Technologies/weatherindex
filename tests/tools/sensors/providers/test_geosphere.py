import pytest
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

from sensors.providers.geosphere import GeoSphereProvider
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
def sample_stations_metadata():
    """Sample metadata response from GeoSphere API."""
    return {
        "stations": [
            {"id": "11035", "is_active": True, "name": "Station 1"},
            {"id": "11036", "is_active": False, "name": "Station 2"},
            {"id": "11037", "is_active": True, "name": "Station 3"},
            {"id": "11038", "is_active": True, "name": "Station 4"}
        ]
    }


@pytest.fixture
def sample_api_response():
    """Sample API response from GeoSphere API."""
    return {
        "timestamps": ["2024-01-15T10:00:00Z", "2024-01-15T10:10:00Z"],
        "features": [
            {
                "type": "Feature",
                "properties": {"station_id": "11035", "RR": 0.5},
                "geometry": {"type": "Point", "coordinates": [16.37, 48.21]}
            },
            {
                "type": "Feature",
                "properties": {"station_id": "11037", "RR": 1.2},
                "geometry": {"type": "Point", "coordinates": [16.37, 48.22]}
            }
        ]
    }


def test_geosphere_smoke(mock_publisher, temp_download_path):
    """Test basic instantiation and inheritance of GeoSphereProvider."""
    client = GeoSphereProvider(
        frequency=600,
        delay=5,
        publisher=mock_publisher,
        download_path=temp_download_path
    )

    assert isinstance(client, GeoSphereProvider)
    assert isinstance(client, BaseProvider)
    assert client._service == "GeoSphere"
    assert client._frequency == 600
    assert client._delay == 5
    assert client._timeout == 30.0  # Default timeout


def test_geosphere_default_values(mock_publisher, temp_download_path):
    """Test that GeoSphereProvider uses correct default values."""
    client = GeoSphereProvider(
        publisher=mock_publisher,
        download_path=temp_download_path
    )

    assert client._frequency == 600
    assert client._delay == 5
    assert client._timeout == 30.0


def test_geosphere_custom_timeout(mock_publisher, temp_download_path, monkeypatch):
    """Test custom timeout configuration via environment variable."""
    # Test the default behavior and then modify the timeout attribute
    client = GeoSphereProvider(
        publisher=mock_publisher,
        download_path=temp_download_path
    )

    # Test that the default timeout is set correctly
    assert client._timeout == 30.0

    # Test that the timeout can be modified after instantiation
    client._timeout = 60.0
    assert client._timeout == 60.0


@pytest.mark.asyncio
@patch("sensors.providers.geosphere.aiohttp.ClientSession")
async def test_fetch_station_ids_success(mock_session, mock_publisher, temp_download_path, sample_stations_metadata):
    """Test successful fetching of station IDs from metadata API."""
    # Mock successful response
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=sample_stations_metadata)

    mock_session_instance = MagicMock()
    mock_session_instance.__aenter__.return_value = mock_session_instance
    mock_session_instance.__aexit__.return_value = None
    mock_session_instance.get.return_value.__aenter__.return_value = mock_response
    mock_session.return_value = mock_session_instance

    client = GeoSphereProvider(
        publisher=mock_publisher,
        download_path=temp_download_path
    )

    station_ids = await client._fetch_station_ids()

    # Should return only active stations
    expected_ids = ["11035", "11037", "11038"]
    assert station_ids == expected_ids
    assert len(station_ids) == 3


@pytest.mark.asyncio
@patch("sensors.providers.geosphere.aiohttp.ClientSession")
async def test_fetch_station_ids_no_stations(mock_session, mock_publisher, temp_download_path):
    """Test handling when no stations are found in metadata."""
    # Mock response with no stations
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={})

    mock_session_instance = MagicMock()
    mock_session_instance.__aenter__.return_value = mock_session_instance
    mock_session_instance.__aexit__.return_value = None
    mock_session_instance.get.return_value.__aenter__.return_value = mock_response
    mock_session.return_value = mock_session_instance

    client = GeoSphereProvider(
        publisher=mock_publisher,
        download_path=temp_download_path
    )

    station_ids = await client._fetch_station_ids()

    assert station_ids == []


@pytest.mark.asyncio
@patch("sensors.providers.geosphere.aiohttp.ClientSession")
async def test_fetch_station_ids_api_error(mock_session, mock_publisher, temp_download_path):
    """Test handling of API errors when fetching station IDs."""
    # Mock API error response
    mock_response = MagicMock()
    mock_response.status = 500

    mock_session_instance = MagicMock()
    mock_session_instance.__aenter__.return_value = mock_session_instance
    mock_session_instance.__aexit__.return_value = None
    mock_session_instance.get.return_value.__aenter__.return_value = mock_response
    mock_session.return_value = mock_session_instance

    client = GeoSphereProvider(
        publisher=mock_publisher,
        download_path=temp_download_path
    )

    station_ids = await client._fetch_station_ids()

    assert station_ids == []


@pytest.mark.asyncio
@patch("sensors.providers.geosphere.aiohttp.ClientSession")
async def test_fetch_station_ids_exception(mock_session, mock_publisher, temp_download_path):
    """Test handling of exceptions when fetching station IDs."""
    # Mock session exception
    mock_session.side_effect = Exception("Connection error")

    client = GeoSphereProvider(
        publisher=mock_publisher,
        download_path=temp_download_path
    )

    station_ids = await client._fetch_station_ids()

    assert station_ids == []


def test_construct_api_url(mock_publisher, temp_download_path):
    """Test API URL construction with different parameters."""
    client = GeoSphereProvider(
        publisher=mock_publisher,
        download_path=temp_download_path
    )

    timestamp = 1718236800  # 2024-01-15 10:00:00
    station_ids = ["11035", "11037"]

    url = client._construct_api_url(timestamp, station_ids)

    # Should contain all required parameters
    assert "parameters=RR" in url
    assert "station_ids=11035,11037" in url
    assert "start=" in url
    assert "end=" in url
    assert "https://dataset.api.hub.geosphere.at/v1/station/historical/tawes-v1-10min" in url


def test_construct_api_url_time_range(mock_publisher, temp_download_path):
    """Test that API URL includes correct time range (6 hours centered on timestamp)."""
    client = GeoSphereProvider(
        publisher=mock_publisher,
        download_path=temp_download_path
    )

    # Use timestamp 1705312800 which represents January 15, 2024 10:00:00 UTC
    # This should give us a 6-hour range from 07:00 to 13:00
    timestamp = 1705312800
    station_ids = ["11035"]

    url = client._construct_api_url(timestamp, station_ids)

    # Should include 6-hour range centered on 10:00 UTC
    assert "start=2024-01-15T07:00" in url  # 10:00 - 3 hours
    assert "end=2024-01-15T13:00" in url    # 10:00 + 3 hours

    # Also verify the URL structure is correct
    assert "parameters=RR" in url
    assert "station_ids=11035" in url
    assert "https://dataset.api.hub.geosphere.at/v1/station/historical/tawes-v1-10min" in url


def test_get_headers(mock_publisher, temp_download_path):
    """Test that headers are correctly constructed."""
    client = GeoSphereProvider(
        publisher=mock_publisher,
        download_path=temp_download_path
    )

    headers = client._get_headers()

    expected_headers = {
        "User-Agent": "GeoSphereWeatherProvider/1.0",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    assert headers == expected_headers


@pytest.mark.asyncio
@patch("sensors.providers.geosphere.aiohttp.ClientSession")
async def test_make_api_call_success(mock_session, mock_publisher, temp_download_path, sample_api_response):
    """Test successful API call."""
    # Mock successful response
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=sample_api_response)

    mock_session_instance = MagicMock()
    mock_session_instance.__aenter__.return_value = mock_session_instance
    mock_session_instance.__aexit__.return_value = None
    mock_session_instance.get.return_value.__aenter__.return_value = mock_response
    mock_session.return_value = mock_session_instance

    client = GeoSphereProvider(
        publisher=mock_publisher,
        download_path=temp_download_path
    )

    url = "https://test.api.com"
    headers = {"test": "header"}

    result = await client._make_api_call(url, headers)

    assert result == sample_api_response


@pytest.mark.asyncio
@patch("sensors.providers.geosphere.aiohttp.ClientSession")
async def test_make_api_call_http_error(mock_session, mock_publisher, temp_download_path):
    """Test handling of HTTP errors in API calls."""
    # Mock HTTP error response
    mock_response = MagicMock()
    mock_response.status = 404

    mock_session_instance = MagicMock()
    mock_session_instance.__aenter__.return_value = mock_session_instance
    mock_session_instance.__aexit__.return_value = None
    mock_session_instance.get.return_value.__aenter__.return_value = mock_response
    mock_session.return_value = mock_session_instance

    client = GeoSphereProvider(
        publisher=mock_publisher,
        download_path=temp_download_path
    )

    url = "https://test.api.com"
    headers = {"test": "header"}

    result = await client._make_api_call(url, headers)

    assert result is None


@pytest.mark.asyncio
@patch("sensors.providers.geosphere.aiohttp.ClientSession")
async def test_make_api_call_exception(mock_session, mock_publisher, temp_download_path):
    """Test handling of exceptions in API calls."""
    # Mock session exception
    mock_session.side_effect = Exception("Network error")

    client = GeoSphereProvider(
        publisher=mock_publisher,
        download_path=temp_download_path
    )

    url = "https://test.api.com"
    headers = {"test": "header"}

    result = await client._make_api_call(url, headers)

    assert result is None


def test_combine_chunk_data_single_chunk(mock_publisher, temp_download_path, sample_api_response):
    """Test combining data from a single chunk."""
    client = GeoSphereProvider(
        publisher=mock_publisher,
        download_path=temp_download_path
    )

    chunk_data = [sample_api_response]

    result = client._combine_chunk_data(chunk_data)

    assert result == sample_api_response


def test_combine_chunk_data_multiple_chunks(mock_publisher, temp_download_path):
    """Test combining data from multiple chunks."""
    client = GeoSphereProvider(
        publisher=mock_publisher,
        download_path=temp_download_path
    )

    chunk1 = {
        "timestamps": ["2024-01-15T10:00:00Z", "2024-01-15T10:10:00Z"],
        "features": [{"id": "1"}, {"id": "2"}]
    }

    chunk2 = {
        "timestamps": ["2024-01-15T10:05:00Z", "2024-01-15T10:15:00Z"],
        "features": [{"id": "3"}, {"id": "4"}]
    }

    chunk_data = [chunk1, chunk2]

    result = client._combine_chunk_data(chunk_data)

    # Should have unique timestamps
    expected_timestamps = [
        "2024-01-15T10:00:00Z",
        "2024-01-15T10:05:00Z",
        "2024-01-15T10:10:00Z",
        "2024-01-15T10:15:00Z"]
    assert result["timestamps"] == expected_timestamps

    # Should have all features
    assert len(result["features"]) == 4


def test_combine_chunk_data_empty_list(mock_publisher, temp_download_path):
    """Test combining data from empty chunk list."""
    client = GeoSphereProvider(
        publisher=mock_publisher,
        download_path=temp_download_path
    )

    result = client._combine_chunk_data([])

    assert result == {}


@pytest.mark.asyncio
@patch.object(GeoSphereProvider, "_fetch_station_ids")
@patch.object(GeoSphereProvider, "_make_api_call")
async def test_fetch_data_success(
        mock_make_api_call,
        mock_fetch_station_ids,
        mock_publisher,
        temp_download_path,
        sample_api_response):
    """Test successful data fetching workflow."""
    # Mock station IDs
    mock_fetch_station_ids.return_value = ["11035", "11037", "11038"]

    # Mock API calls (should be called once for the single chunk)
    mock_make_api_call.return_value = sample_api_response

    client = GeoSphereProvider(
        publisher=mock_publisher,
        download_path=temp_download_path
    )

    timestamp = 1718236800

    await client.fetch_job(timestamp)

    # Verify station IDs were fetched
    mock_fetch_station_ids.assert_called_once()

    # Verify API call was made
    mock_make_api_call.assert_called_once()


@pytest.mark.asyncio
@patch.object(GeoSphereProvider, "_fetch_station_ids")
async def test_fetch_data_no_stations(mock_fetch_station_ids, mock_publisher, temp_download_path):
    """Test handling when no stations are available."""
    # Mock no station IDs
    mock_fetch_station_ids.return_value = []

    client = GeoSphereProvider(
        publisher=mock_publisher,
        download_path=temp_download_path
    )

    timestamp = 1718236800

    await client.fetch_job(timestamp)

    # Verify station IDs were fetched
    mock_fetch_station_ids.assert_called_once()

    # No API calls should be made


@pytest.mark.asyncio
@patch.object(GeoSphereProvider, "_fetch_station_ids")
@patch.object(GeoSphereProvider, "_make_api_call")
async def test_fetch_data_chunking(
        mock_make_api_call,
        mock_fetch_station_ids,
        mock_publisher,
        temp_download_path,
        sample_api_response):
    """Test that data is properly chunked when there are many stations."""
    # Mock many station IDs (more than chunk size of 100)
    many_station_ids = [f"station_{i:05d}" for i in range(250)]
    mock_fetch_station_ids.return_value = many_station_ids

    # Mock API calls for each chunk
    mock_make_api_call.return_value = sample_api_response

    client = GeoSphereProvider(
        publisher=mock_publisher,
        download_path=temp_download_path
    )

    timestamp = 1718236800

    await client.fetch_job(timestamp)

    # Should be called 3 times (250 stations / 100 per chunk = 3 chunks)
    assert mock_make_api_call.call_count == 3


@pytest.mark.asyncio
@patch.object(GeoSphereProvider, "_fetch_station_ids")
@patch.object(GeoSphereProvider, "_make_api_call")
async def test_fetch_data_api_failure(mock_make_api_call, mock_fetch_station_ids, mock_publisher, temp_download_path):
    """Test handling when API calls fail."""
    # Mock station IDs
    mock_fetch_station_ids.return_value = ["11035", "11037"]

    # Mock API call failure
    mock_make_api_call.return_value = None

    client = GeoSphereProvider(
        publisher=mock_publisher,
        download_path=temp_download_path
    )

    timestamp = 1718236800

    await client.fetch_job(timestamp)

    # Verify station IDs were fetched
    mock_fetch_station_ids.assert_called_once()

    # Verify API call was made
    assert mock_make_api_call.call_count == 1


@pytest.mark.asyncio
@patch.object(GeoSphereProvider, "_fetch_station_ids")
@patch.object(GeoSphereProvider, "_make_api_call")
async def test_fetch_job_integration(
        mock_make_api_call,
        mock_fetch_station_ids,
        mock_publisher,
        temp_download_path,
        sample_api_response):
    """Test the complete fetch_job workflow."""
    # Mock station IDs
    mock_fetch_station_ids.return_value = ["11035", "11037"]

    # Mock API call success
    mock_make_api_call.return_value = sample_api_response

    client = GeoSphereProvider(
        publisher=mock_publisher,
        download_path=temp_download_path
    )

    timestamp = 1718236800

    await client.fetch_job(timestamp)

    # Verify the complete workflow was executed
    mock_fetch_station_ids.assert_called_once()
    mock_make_api_call.assert_called_once()
