import asyncio
import os
import shutil

from abc import abstractmethod
from concurrent.futures import ProcessPoolExecutor

from forecast.publishers.publisher import Publisher
from forecast.utils.time import Timestamp, time_to_next_run
from forecast.sensor import Sensor
from functools import partial
from itertools import islice
from typing import Awaitable, Callable, Generator, TypeVar
from typing_extensions import override  # for python <3.12

from rich.console import Console

console = Console()


T = TypeVar("T")


class BaseProvider:
    def __init__(self,
                 publisher: Publisher,
                 download_path: str,
                 frequency: int = 600,
                 delay: int = 0):
        """
        Initialize the provider.

        Parameters
        ----------
        frequency : int
            The frequency of the provider in seconds.
        delay : int
            Additional delay in seconds. It used to wait for the data to be available.
        publisher : Publisher
            The publisher to publish the data. Local storage or any cloud storage.
        download_path : str
            The path to store the downloaded data.
        process_num : int
            The number of processes to use for downloading the data.
        """
        self._frequency = frequency
        self._delay = delay
        self._download_path = download_path
        self._publisher = publisher

    async def run(self):
        """
        Run the provider.
        """
        while True:
            time_to_sleep = time_to_next_run(self._frequency) + self._delay
            console.log(f"Next data for will be available in {time_to_sleep} seconds.")
            await asyncio.sleep(time_to_sleep)

            start_time = Timestamp.get_current()
            timestamp = Timestamp.floor(start_time, self._frequency)

            snapshot_path = self.snapshot_path(timestamp)

            shutil.rmtree(snapshot_path, ignore_errors=True)
            os.makedirs(snapshot_path, exist_ok=False)

            await self.fetch_job(timestamp)

            shutil.make_archive(base_name=snapshot_path,
                                format="zip",
                                root_dir=self._download_path,
                                base_dir=str(timestamp))
            archive_path = f"{snapshot_path}.zip"

            # Publish to the storage
            await self._publisher.publish(snapshot_path=archive_path)

            # Remove the file
            try:
                console.log(f"Removing file {archive_path}")
                shutil.rmtree(snapshot_path, ignore_errors=True)
                os.remove(archive_path)
            except Exception as e:
                console.log(f"Error removing file {archive_path}: {e}")

            console.log(f"It took {Timestamp.get_current() - start_time} seconds to download data")

    def snapshot_path(self, timestamp: int) -> str:
        return os.path.join(self._download_path, str(timestamp))

    @abstractmethod
    async def fetch_job(self, timestamp: int):
        """
        Fetch the data for the given timestamp

        Parameters
        ----------
        timestamp : int
            The timestamp of the data to fetch
        """
        pass


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


class BaseParallelExecutionProvider(BaseProvider):
    """
    Base class for parallel execution providers.
    """

    def __init__(self,
                 process_num: int,
                 chunk_size: int,
                 **kwargs):
        super().__init__(**kwargs)

        self._process_num = process_num
        self._chunk_size = chunk_size

        console.log(f"Using {self._process_num} processes and {self._chunk_size} chunk size")

    async def execute_with_batches(self,
                                   args: list[T],
                                   chunk_func: Callable[[list[T]], list[R]]) -> list[R]:
        loop = asyncio.get_running_loop()
        with ProcessPoolExecutor(max_workers=self._process_num) as pool:
            tasks = [loop.run_in_executor(pool, chunk_func, chunk) for chunk in batched(args, self._chunk_size)]
            chunk_results = await asyncio.gather(*tasks, return_exceptions=True)
        return [item for chunk in chunk_results for item in chunk]


def _process_sensor_chunk(sensors: list[Sensor],
                          download_path: str,
                          get_json: Callable[[float, float], Awaitable[str | bytes | None]]) -> list[object]:

    async def _process_sensor(sensor: Sensor) -> None:
        try:
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
        except Exception as e:
            console.print_exception()

    async def _process(sensors: list[Sensor]) -> list[object]:
        jobs = [_process_sensor(sensor) for sensor in sensors]
        return await asyncio.gather(*jobs, return_exceptions=True)

    return asyncio.run(_process(sensors))


class BaseForecastInPointProvider(BaseParallelExecutionProvider):
    def __init__(self,
                 sensors: list[Sensor],
                 process_num: int | None = None,
                 chunk_size: int | None = None,
                 **kwargs):
        process_num = os.cpu_count() if process_num is None else process_num
        chunk_size = len(sensors) // process_num if chunk_size is None else chunk_size

        super().__init__(process_num=process_num,
                         chunk_size=chunk_size,
                         **kwargs)

        self.sensors = sensors
        console.log(f"Requesting forecast for {len(self.sensors)} sensors")

    @abstractmethod
    async def get_json_forecast_in_point(self, lon: float, lat: float) -> str | bytes | None:
        raise NotImplementedError("Getting JSON forecast in point was not implemented")

    @override
    async def fetch_job(self, timestamp: int):
        snapshot_path = self.snapshot_path(timestamp)

        op = partial(_process_sensor_chunk,
                     download_path=snapshot_path,
                     get_json=self.get_json_forecast_in_point)

        await self.execute_with_batches(self.sensors, op)
