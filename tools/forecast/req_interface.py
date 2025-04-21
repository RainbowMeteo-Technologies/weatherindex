import json
import requests
import typing

from rich.console import Console

console = Console()


class RequestInterface:

    def do(self, lon: float, lat: float) -> typing.Tuple[bytes, str]:
        try:
            return self._do_impl(lon=lon, lat=lat)
        except BaseException:
            console.print_exception()
            return None

    def _do_impl(self, lon: float, lat: float) -> bytes:
        raise NotImplemented()

    def _run_with_retries(self, do_request, n: int = 5):
        data = None
        for _ in range(n):
            data = do_request()
            if data is not None:
                break

        return data

    def _native_get(self, url: str, headers: dict = {}, params: dict = {}) -> typing.Tuple[bytes, str]:
        """Does http GET-request to specified url
        """
        def _try_download():
            try:
                response = requests.get(url, headers=headers, params=params, timeout=30)
                if response.status_code == 200:
                    return response.content
                else:
                    console.log(f"{response.status_code} - {url}")
                    try:
                        msg = json.loads(response.content)
                        console.log(f"GET-request response message: {msg}")
                    except BaseException:
                        console.log(f"GET-request response is not JSON")
                    return None
            except requests.exceptions.RequestException:
                return None

        return self._run_with_retries(_try_download)

    def _native_post(self, url: str, headers: dict = {}, body={}) -> typing.Tuple[bytes, str]:
        """Does http POST-request to specified url
        """
        def _try_download():
            try:
                response = requests.post(url, json=body, headers=headers, timeout=30)
                if response.status_code == 200:
                    return response.content
                else:
                    console.log(f"{response.status_code} - {url}")
                    try:
                        msg = json.loads(response.content)
                        console.log(f"POST-request error message: {msg}")
                    except BaseException:
                        console.log(f"POST-request response is not JSON")
                    return None
            except requests.exceptions.RequestException:
                return None

        return self._run_with_retries(_try_download)
