from unittest.mock import AsyncMock, patch

import pytest

from sensors.providers.fsdiopendata import FSDIOpenDataProvider


class TestFSDIOpenDataProvider:
    """Test FSDIOpenData provider functionality."""

    @pytest.fixture
    def mock_publisher(self):
        """Create a mock publisher for testing"""
        publisher = AsyncMock()
        return publisher

    @pytest.fixture
    def temp_download_path(self, tmp_path):
        """Create a temporary download path for testing"""
        return str(tmp_path)

    def test_fsdiopendata_smoke(self, mock_publisher, temp_download_path):
        """Test basic instantiation and inheritance of FSDIOpenDataProvider."""
        client = FSDIOpenDataProvider(
            publisher=mock_publisher,
            download_path=temp_download_path,
            frequency=600,
            delay=5
        )

        assert client is not None
        assert isinstance(client, FSDIOpenDataProvider)
        assert client._service == "FSDIOpenData"
        assert client._timeout == 30.0

    def test_fsdiopendata_default_values(self, mock_publisher, temp_download_path):
        """Test that FSDIOpenDataProvider uses correct default values."""
        client = FSDIOpenDataProvider(
            publisher=mock_publisher,
            download_path=temp_download_path
        )

        assert client._frequency == 600
        assert client._delay == 5
        assert client._timeout == 30.0

    @pytest.mark.asyncio
    async def test_fetch_stac_data_failure(self, mock_publisher, temp_download_path):
        """Test STAC API data fetching failure."""
        with patch("sensors.providers.fsdiopendata.aiohttp.ClientSession") as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 404

            mock_session_instance = AsyncMock()
            mock_session_instance.__aenter__.return_value = mock_session_instance
            mock_session_instance.__aexit__.return_value = None

            # Fix the async context manager mocking
            mock_get_response = AsyncMock()
            mock_get_response.__aenter__.return_value = mock_response
            mock_get_response.__aexit__.return_value = None
            mock_session_instance.get.return_value = mock_get_response

            mock_session.return_value = mock_session_instance

            client = FSDIOpenDataProvider(
                publisher=mock_publisher,
                download_path=temp_download_path
            )

            result = await client._fetch_stac_data()

            assert result is None

    def test_get_headers(self, mock_publisher, temp_download_path):
        """Test that headers are correctly set."""
        client = FSDIOpenDataProvider(
            publisher=mock_publisher,
            download_path=temp_download_path
        )

        headers = client._get_headers()

        assert headers["User-Agent"] == "FSDIOpenDataWeatherProvider/1.0"
        assert headers["Accept"] == "application/json,text/csv,*/*"

    @pytest.mark.asyncio
    async def test_download_csv_files_missing_asset(self, mock_publisher, temp_download_path):
        """Test CSV downloading with missing '_t_now.csv' asset."""
        sample_stac_data = {
            "features": [
                {
                    "id": "abe",
                    "assets": {
                        "ogd-smn-precip_abe_d_historical.csv": {
                            "href": "https://example.com/abe_d_historical.csv"
                        }
                    }
                }
            ]
        }

        client = FSDIOpenDataProvider(
            publisher=mock_publisher,
            download_path=temp_download_path
        )

        result = await client._download_csv_files(sample_stac_data, temp_download_path)

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_create_combined_archive(self, mock_publisher, temp_download_path, tmp_path):
        """Test combined archive creation."""
        import os
        import tempfile

        # Create temporary files
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file1 = os.path.join(temp_dir, "test1.txt")
            test_file2 = os.path.join(temp_dir, "test2.txt")

            with open(test_file1, "w") as f:
                f.write("test content 1")
            with open(test_file2, "w") as f:
                f.write("test content 2")

            archive_path = os.path.join(temp_dir, "test.zip")

            client = FSDIOpenDataProvider(
                publisher=mock_publisher,
                download_path=temp_download_path
            )

            await client._create_combined_archive([test_file1, test_file2], archive_path)

            assert os.path.exists(archive_path)

            # Verify archive contents
            import zipfile
            with zipfile.ZipFile(archive_path, "r") as zip_file:
                file_list = zip_file.namelist()
                assert "test1.txt" in file_list
                assert "test2.txt" in file_list
