import aiohttp
import json

from dataclasses import dataclass
from rich.console import Console
from typing import Awaitable, Callable


console = Console()


@dataclass
class Response:
    status: int = 0  # http status code, 0 if failed for any other reason
    payload: bytes | str | None = None

    @property
    def ok(self) -> bool:
        return (200 <= self.status < 300) and (self.payload is not None)

    def set_failed(self):
        self.status = 0


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

            client_timeout = aiohttp.ClientTimeout(total=timeout)

            async def _try_download() -> Response:
                try:
                    async with session.get(url,
                                           headers=headers,
                                           params=params,
                                           timeout=client_timeout) as resp:
                        if resp.ok:
                            return Response(status=resp.status,
                                            payload=(await resp.read()))
                        else:
                            console.log(f"{resp.status} - {url}")
                        return Response(status=resp.status)

                except Exception as e:
                    return Response()
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
                    client_timeout = aiohttp.ClientTimeout(total=timeout)
                    async with session.post(url,
                                            headers=headers,
                                            json=body,
                                            timeout=client_timeout) as resp:
                        if resp.ok:
                            return Response(status=resp.status,
                                            payload=(await resp.read()))
                        else:
                            console.log(f"{resp.status} - {url}")
                        return Response(status=resp.status)
                except Exception as e:
                    return Response()

            return await self._run_with_retries(_try_download)
