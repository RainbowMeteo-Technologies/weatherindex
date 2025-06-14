import aiohttp
import json

from rich.console import Console
from typing import Awaitable, Callable


console = Console()


class RequestInterface():

    async def _run_with_retries(self,
                                do_request: Callable[[], Awaitable[bytes | None]],
                                n: int = 5) -> bytes | None:
        for _ in range(n):
            data = await do_request()
            if data is not None:
                return data
        return None

    async def _native_get(self, url: str,
                          headers: dict[str, str] | None = None,
                          params: dict[str, str] | None = None,
                          timeout: int = 30) -> bytes | None:
        """Does http GET-request to specified url
        """
        async with aiohttp.ClientSession() as session:

            async def _try_download() -> bytes | None:
                client_timeout = aiohttp.ClientTimeout(total=timeout)
                try:
                    async with session.get(url,
                                           headers=headers,
                                           params=params,
                                           timeout=client_timeout) as resp:
                        if resp.ok:
                            return await resp.read()
                        else:
                            console.log(f"{resp.status} - {url}")
                        return None

                except Exception:
                    return None

            return await self._run_with_retries(_try_download)

    async def _native_post(self, url: str,
                           headers: dict[str, str] | None = None,
                           body: dict[str, object] = {},
                           timeout: int = 30) -> bytes | None:
        """Does http POST-request to specified url
        """
        async with aiohttp.ClientSession() as session:

            async def _try_download() -> bytes | None:
                try:
                    client_timeout = aiohttp.ClientTimeout(total=timeout)
                    async with session.post(url,
                                            headers=headers,
                                            json=body,
                                            timeout=client_timeout) as resp:
                        if resp.ok:
                            return await resp.read()
                        else:
                            console.log(f"{resp.status} - {url}")
                        return None
                except Exception:
                    return None

            return await self._run_with_retries(_try_download)
