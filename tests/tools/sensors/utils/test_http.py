import pytest

from sensors.utils.http import Http
from unittest.mock import AsyncMock, MagicMock, patch


def _session_returning(status: int, body: bytes) -> MagicMock:
    response = MagicMock()
    response.status = status
    response.read = AsyncMock(return_value=body)
    session = MagicMock()
    session.get = AsyncMock(return_value=response)
    return session


@pytest.mark.asyncio
async def test_partial_content_response_is_returned():
    session = _session_returning(206, b"tail")

    data = await Http.get_with_session("https://example.com/file.txt",
                                       session=session,
                                       headers={"Range": "bytes=-4"})

    assert data == b"tail"
    session.get.assert_called_once_with("https://example.com/file.txt", headers={"Range": "bytes=-4"})


@pytest.mark.asyncio
@patch("sensors.utils.http.asyncio.sleep", new_callable=AsyncMock)
async def test_error_response_is_retried_and_gives_none(mock_sleep):
    session = _session_returning(503, b"")

    data = await Http.get_with_session("https://example.com/file.txt", session=session, retry_count=3)

    assert data is None
    assert session.get.call_count == 3
