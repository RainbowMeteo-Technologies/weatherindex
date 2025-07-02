import json
import os
import pytest
import tempfile

from forecast.providers.rainviewer import RainViewer
from forecast.utils.constants import FETCHING_REPORT_NAME
from forecast.utils.req_interface import Response
from unittest.mock import AsyncMock, MagicMock, patch


def test_rainviewer_smoke():
    client = RainViewer(token="test_token",
                        zoom=1,
                        download_path="test_download_path",
                        publisher=MagicMock(),
                        process_num=1,
                        chunk_size=1)
    assert isinstance(client, RainViewer)
    assert client.token == "test_token"
    assert client.zoom == 1


@pytest.mark.asyncio
@patch.object(RainViewer, "execute_with_batches", new_callable=AsyncMock)
@patch.object(RainViewer, "_native_get", new_callable=AsyncMock)
async def test_get_forecast(mock_get, mock_execute):
    zoom_level = 1
    num_tiles_per_side = 2 ** zoom_level
    total_tiles = num_tiles_per_side * num_tiles_per_side
    num_frames = 7  # 1 current + 6 nowcast
    num_mask_tiles = total_tiles  # One mask tile per map tile
    total_jobs = (total_tiles * num_frames) + num_mask_tiles

    mock_metadata = {
        "host": "https://test-host.com",
        "radar": {
            "past": [
                {"time": 1234567890, "path": "/test/path"}
            ],
            "nowcast": [
                {"time": 1234567950, "path": "/test/path/1"},
                {"time": 1234568010, "path": "/test/path/2"},
                {"time": 1234568070, "path": "/test/path/3"},
                {"time": 1234568130, "path": "/test/path/4"},
                {"time": 1234568190, "path": "/test/path/5"},
                {"time": 1234568250, "path": "/test/path/6"}
            ]
        }
    }

    mock_get.return_value = Response(
        status=200,
        payload=json.dumps(mock_metadata).encode()
    )
    mock_execute.return_value = [Response(status=200, payload=b"test")] * total_jobs

    with tempfile.TemporaryDirectory() as temp_dir:
        download_path = os.path.join(temp_dir, "download")
        os.makedirs(download_path)

        client = RainViewer(token="test_token",
                            zoom=zoom_level,
                            download_path=download_path,
                            publisher=MagicMock(),
                            process_num=1,
                            chunk_size=1)

        timestamp = 1234567890
        await client.fetch_job(timestamp=timestamp)
        assert os.path.exists(os.path.join(download_path, str(timestamp), FETCHING_REPORT_NAME))

        # Verify metadata was requested
        mock_get.assert_called_once_with(url="https://api.rainviewer.com/private/test_token/weather-maps.json")

        # Verify execute_with_batches was called with correct number of jobs
        assert mock_execute.call_count == 1
        call_args = mock_execute.call_args
        assert call_args is not None
        jobs = call_args[1]["args"]
        assert len(jobs) == total_jobs

        # Verify all responses were successful
        responses = mock_execute.return_value
        assert all(resp.ok for resp in responses)
        assert all(resp.status == 200 for resp in responses)


@pytest.mark.asyncio
@patch.object(RainViewer, "_native_get", new_callable=AsyncMock)
async def test_get_forecast_metadata_error(mock_get):
    mock_get.return_value = Response(status=0)  # Failed response

    with tempfile.TemporaryDirectory() as temp_dir:
        timestamp = 1234567890
        download_path = os.path.join(temp_dir, str(timestamp))
        os.makedirs(download_path)

        client = RainViewer(token="test_token",
                            zoom=1,
                            download_path=download_path,
                            publisher=MagicMock(),
                            process_num=1,
                            chunk_size=1)
        await client.fetch_job(timestamp=timestamp)

        # Verify metadata request was made
        mock_get.assert_called_once_with(url="https://api.rainviewer.com/private/test_token/weather-maps.json")


@pytest.mark.asyncio
@patch.object(RainViewer, "_native_get", new_callable=AsyncMock)
async def test_get_forecast_snapshot_not_available(mock_get):
    # Test case for when requested snapshot is not available
    mock_metadata = {
        "host": "https://test-host.com",
        "radar": {
            "past": [
                {"time": 1234567890, "path": "/test/path"}
            ],
            "nowcast": []
        }
    }

    mock_get.return_value = Response(
        status=200,
        payload=json.dumps(mock_metadata).encode()
    )

    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a subdirectory with a different timestamp
        download_path = os.path.join(temp_dir, "1234567891")
        os.makedirs(download_path)

        client = RainViewer(token="test_token",
                            zoom=1,
                            download_path=download_path,
                            publisher=MagicMock(),
                            process_num=1,
                            chunk_size=1)

        await client.fetch_job(timestamp=1234567891)

        # Verify metadata was requested
        mock_get.assert_called_once_with(url="https://api.rainviewer.com/private/test_token/weather-maps.json")
