import asyncio
import os
import pickle

from abc import ABC, abstractmethod
from concurrent.futures import ProcessPoolExecutor
from forecast.req_interface import RequestInterface
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


def _process_sensor_chunk(sensors: list[Sensor],
                          download_path: str,
                          get_json: Callable[[float, float], Awaitable[str | bytes | None]]) -> list[object]:

    async def _process_sensor(sensor: Sensor) -> None:
        forecast = await get_json(sensor.lon, sensor.lat)
        if forecast is not None:
            file_mode = None
            if isinstance(forecast, str):
                file_mode = "w"
            elif isinstance(forecast, bytes):
                file_mode = "wb"
            else:
                raise TypeError(f"Expected str or bytes, got {type(forecast).__name__}")

            with open(os.path.join(download_path, f"{sensor.id}.json"), file_mode) as f:
                f.write(forecast)
        else:
            console.log(f"Wasn't able to get data for {sensor.id}")

    async def _process(sensors: list[Sensor]) -> list[object]:
        jobs = [_process_sensor(sensor) for sensor in sensors]
        return await asyncio.gather(*jobs, return_exceptions=True)

    return asyncio.run(_process(sensors))


class SensorClientBase(ClientBase):
    def __init__(self, sensors: list[Sensor]):
        self.sensors = sensors

    @abstractmethod
    async def _get_json_forecast_in_point(self, lon: float, lat: float) -> str | bytes | None:
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

        await self.execute_with_batches(self.sensors, op, chunk_size, process_num)
