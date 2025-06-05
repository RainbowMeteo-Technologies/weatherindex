import asyncio
import os
import pickle
import pandas as pd

from abc import ABC, abstractmethod
from concurrent.futures import ProcessPoolExecutor
from forecast.req_interface import RequestInterface, Response
from forecast.sensor import Sensor
from functools import partial
from itertools import islice
from rich.console import Console
from typing import Awaitable, Callable, Generator, TypeVar
from typing_extensions import override


console = Console()


T = TypeVar("T")


def batched(iterable: list[T], n: int) -> Generator[list[T], None, None]:
    """Batch data into lists of length n. The last batch may be shorter.
    batched("ABCDEFG", 3) --> ABC DEF G
    for use with python <3.12
    """
    if n < 1:
        raise ValueError("n must be at least one")
    it = iter(iterable)
    while batch := list(islice(it, n)):
        yield batch


R = TypeVar("R")


class ClientBase(RequestInterface, ABC):

    async def execute_with_batches(self,
                                   args: list[T],
                                   chunk_func: Callable[[list[T]], list[R]],
                                   chunk_size: int,
                                   process_num: int) -> list[R]:
        loop = asyncio.get_running_loop()
        with ProcessPoolExecutor(max_workers=process_num) as pool:
            tasks = [loop.run_in_executor(pool, chunk_func, chunk) for chunk in batched(args, chunk_size)]
            chunk_results = await asyncio.gather(*tasks, return_exceptions=True)
        return [item for chunk in chunk_results for item in chunk]

    @abstractmethod
    async def get_forecast(self,
                           download_path: str,
                           process_num: int | None = None,
                           chunk_size: int | None = None):
        pass

    def save_fetching_report(self,
                             folder: str,
                             targets: list[str],
                             statuses: list[bool],
                             error_types: list[str] | None = None,
                             error_messages: list[str] | None = None):
        report = pd.DataFrame({"target": targets, "status": statuses})
        if error_types is not None:
            report["error_types"] = error_types
        if error_messages is not None:
            report["error_messages"] = error_messages
        report.to_csv(os.path.join(folder, "fetching-report.csv"), index=False)


def _process_sensor_chunk(sensors: list[Sensor],
                          download_path: str,
                          get_json: Callable[[float, float], Awaitable[Response]]) -> list[Response]:

    async def _process_sensor(sensor: Sensor) -> Response:
        resp = await get_json(sensor.lon, sensor.lat)
        if resp.forecast is not None:
            try:
                file_mode = None
                if isinstance(resp.forecast, str):
                    file_mode = "w"
                elif isinstance(resp.forecast, bytes):
                    file_mode = "wb"
                else:
                    raise TypeError(f"Expected str or bytes, got {type(resp.forecast).__name__}")

                with open(os.path.join(download_path, f"{sensor.id}.json"), file_mode) as f:
                    f.write(resp.forecast)
            except Exception as e:
                resp.error_type = type(e).__name__
                resp.error_message = str(e)
        else:
            console.log(f"Wasn't able to get data for {sensor.id}")
        return resp

    async def _process(sensors: list[Sensor]) -> list[Response]:
        jobs = [_process_sensor(sensor) for sensor in sensors]
        return await asyncio.gather(*jobs, return_exceptions=True)

    return asyncio.run(_process(sensors))


class SensorClientBase(ClientBase):
    def __init__(self, sensors: list[Sensor]):
        self.sensors = sensors

    @abstractmethod
    async def _get_json_forecast_in_point(self, lon: float, lat: float) -> Response:
        raise NotImplementedError("Getting JSON forecast in point was not implemented")

    @override
    async def get_forecast(self,
                           download_path: str,
                           process_num: int | None = None,
                           chunk_size: int | None = None):
        """Could be overriden"""

        process_num = os.cpu_count() if process_num is None else process_num
        chunk_size = len(self.sensors) // process_num if chunk_size is None else chunk_size

        op = partial(_process_sensor_chunk,
                     download_path=download_path,
                     get_json=self._get_json_forecast_in_point)

        responses = await self.execute_with_batches(self.sensors, op, chunk_size, process_num)

        self.save_fetching_report(
            targets=[sensor.id for sensor in self.sensors],
            statuses=[resp.error_type is None and resp.forecast is not None for resp in responses],
            error_types=[resp.error_type for resp in responses],
            error_messages=[resp.error_message for resp in responses],
            folder=download_path
        )
