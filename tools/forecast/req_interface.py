import aiohttp
import json

from dataclasses import dataclass
from rich.console import Console
from typing import Awaitable, Callable
from typing_extensions import override  # for python <3.12


console = Console()


@dataclass
class Response:
    status: int | None = None  # http status code
    payload: bytes | str | None = None
    error_type: str | None = None
    error_message: str | None = None
    forecast: str | None = None


class RequestInterface():

    async def _run_with_retries(self,
                                do_request: Callable[[], Awaitable[Response]],
                                n: int = 5) -> Response:
        for _ in range(n):
            resp = await do_request()
            if resp.payload is not None:
                return resp
        return resp  # return latest response if no valid response encountered

    async def _native_get(self, url: str,
                          headers: dict[str, str] | None = None,
                          params: dict[str, str] | None = None,
                          timeout: int = 30) -> Response:
        """Does http GET-request to specified url
        """
        async with aiohttp.ClientSession() as session:

            async def _try_download() -> Response:
                try:
                    timeout = aiohttp.ClientTimeout(total=timeout)
                    async with session.get(url, headers=headers, params=params, timeout=timeout) as resp:
                        if resp.ok:
                            return Response(status=resp.status,
                                            payload=(await resp.read()))
                        else:
                            console.log(f"{resp.status} - {url}")
                        return Response(status=resp.status, error_type="Downloading error")

                except Exception as e:
                    return Response(error_type=type(e).__name__,
                                    error_message=str(e))
            return await self._run_with_retries(_try_download)

    async def _native_post(self, url: str,
                           headers: dict[str, str] | None = None,
                           body: dict[str, object] = {},
                           timeout: int = 30) -> Response:
        """Does http POST-request to specified url
        """
        async with aiohttp.ClientSession() as session:

            async def _try_download() -> Response:
                try:
                    timeout = aiohttp.ClientTimeout(total=timeout)
                    async with session.post(url, headers=headers, json=body, timeout=timeout) as resp:
                        if resp.ok:
                            return Response(status=resp.status,
                                            payload=(await resp.read()))
                        else:
                            console.log(f"{resp.status} - {url}")
                        return Response(status=resp.status, error_type="Downloading error")
                except Exception as e:
                    return Response(error_type=type(e).__name__,
                                    error_message=str(e))

            return await self._run_with_retries(_try_download)
