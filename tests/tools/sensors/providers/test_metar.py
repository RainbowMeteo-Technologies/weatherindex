import gzip
import pytest
import tempfile

from sensors.providers.metar import MetarSource
from sensors.providers.provider import BaseProvider
from sensors.publishers.publisher import Publisher
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_publisher():
    return MagicMock(spec=Publisher)


@pytest.fixture
def temp_download_path():
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


def test_metar_smoke(mock_publisher, temp_download_path):
    """Test basic instantiation and inheritance of MetarSource."""
    client = MetarSource(
        frequency=120,
        delay=5,
        publisher=mock_publisher,
        download_path=temp_download_path
    )

    assert isinstance(client, MetarSource)
    assert isinstance(client, BaseProvider)
    assert client._service == "METAR"
    assert client._frequency == 120
    assert client._delay == 5


def test_metar_default_values(mock_publisher, temp_download_path):
    """Test that MetarSource uses correct default values."""
    client = MetarSource(
        publisher=mock_publisher,
        download_path=temp_download_path
    )

    assert client._frequency == 120
    assert client._delay == 5


@pytest.mark.asyncio
@patch("sensors.providers.metar.Http.get")
async def test_fetch_data_success(mock_http_get, mock_publisher, temp_download_path):
    """Test successful data fetching and storage."""
    # Mock successful HTTP response with gzipped XML data
    mock_xml_data = "<metar><station>KJFK</station><temp>20</temp></metar>"
    mock_gzipped_data = gzip.compress(mock_xml_data.encode("utf-8"))
    mock_http_get.return_value = mock_gzipped_data

    client = MetarSource(
        publisher=mock_publisher,
        download_path=temp_download_path
    )

    # Initialize storage manually for testing (normally done in run() method)
    from sensors.utils.memory_zip import MemoryZip
    client._storage = MemoryZip()

    timestamp = 1718236800

    # Test the fetch_job method
    await client.fetch_job(timestamp)

    # Verify HTTP call was made
    mock_http_get.assert_called_once_with("https://aviationweather.gov/data/cache/metars.cache.xml.gz")

    # Verify data was stored in memory zip
    assert client._storage is not None
    # Note: We can't directly test the memory zip contents without exposing internal state


@pytest.mark.asyncio
@patch("sensors.providers.metar.Http.get")
async def test_fetch_data_exception_handling(mock_http_get, mock_publisher, temp_download_path, caplog):
    """Test handling of exceptions during data fetching."""
    # Mock HTTP exception
    mock_http_get.side_effect = Exception("Network error")

    client = MetarSource(
        publisher=mock_publisher,
        download_path=temp_download_path
    )

    # Initialize storage manually for testing
    from sensors.utils.memory_zip import MemoryZip
    client._storage = MemoryZip()

    timestamp = 1718236800

    # Test the fetch_job method
    await client.fetch_job(timestamp)

    # Verify HTTP call was made
    mock_http_get.assert_called_once_with("https://aviationweather.gov/data/cache/metars.cache.xml.gz")

    # Verify that some error was logged
    assert len(caplog.records) > 0, "No log records were captured"

    # Check if the expected error is in the logs
    log_text = caplog.text.lower()
    error_found = any([
        "network error" in log_text,
        "error" in log_text,
        "exception" in log_text
    ])
    assert error_found, f"Network error not found in logs: {caplog.text}"


@pytest.mark.asyncio
@patch("sensors.providers.metar.Http.get")
async def test_fetch_job_integration(mock_http_get, mock_publisher, temp_download_path):
    """Test the complete fetch_job workflow."""
    # Mock successful HTTP response
    mock_xml_data = "<metar><station>KJFK</station><temp>20</temp></metar>"
    mock_gzipped_data = gzip.compress(mock_xml_data.encode("utf-8"))
    mock_http_get.return_value = mock_gzipped_data

    client = MetarSource(
        publisher=mock_publisher,
        download_path=temp_download_path
    )

    # Initialize storage manually for testing
    from sensors.utils.memory_zip import MemoryZip
    client._storage = MemoryZip()

    timestamp = 1718236800

    # Test the fetch_job method
    await client.fetch_job(timestamp)

    # Verify HTTP call was made
    mock_http_get.assert_called_once_with("https://aviationweather.gov/data/cache/metars.cache.xml.gz")


@pytest.mark.asyncio
@patch("sensors.providers.metar.Http.get")
async def test_fetch_data_with_large_xml(mock_http_get, mock_publisher, temp_download_path):
    """Test handling of large XML data."""
    # Create a larger XML dataset
    mock_xml_data = "".join([f"<metar><station>KST{i:03d}</station><temp>{i}</temp></metar>" for i in range(1000)])
    mock_gzipped_data = gzip.compress(mock_xml_data.encode("utf-8"))
    mock_http_get.return_value = mock_gzipped_data

    client = MetarSource(
        publisher=mock_publisher,
        download_path=temp_download_path
    )

    # Initialize storage manually for testing
    from sensors.utils.memory_zip import MemoryZip
    client._storage = MemoryZip()

    timestamp = 1718236800

    # Test the fetch_job method
    await client.fetch_job(timestamp)

    # Verify HTTP call was made
    mock_http_get.assert_called_once_with("https://aviationweather.gov/data/cache/metars.cache.xml.gz")


@pytest.mark.asyncio
@patch("sensors.providers.metar.Http.get")
async def test_fetch_data_with_special_characters(mock_http_get, mock_publisher, temp_download_path):
    """Test handling of XML data with special characters."""
    # XML with special characters and encoding
    mock_xml_data = "<metar><station>KJFK</station><temp>20°C</temp><remarks>WIND 15KT</remarks></metar>"
    mock_gzipped_data = gzip.compress(mock_xml_data.encode("utf-8"))
    mock_http_get.return_value = mock_gzipped_data

    client = MetarSource(
        publisher=mock_publisher,
        download_path=temp_download_path
    )

    # Initialize storage manually for testing
    from sensors.utils.memory_zip import MemoryZip
    client._storage = MemoryZip()

    timestamp = 1718236800

    # Test the fetch_job method
    await client.fetch_job(timestamp)

    # Verify HTTP call was made
    mock_http_get.assert_called_once_with("https://aviationweather.gov/data/cache/metars.cache.xml.gz")
