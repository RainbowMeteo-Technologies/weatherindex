from abc import ABC, abstractmethod

from rich.console import Console

console = Console()


class Publisher(ABC):
    @abstractmethod
    async def publish(self, snapshot_path: str) -> None:
        """
        Publish data from the storage to the destination.

        Parameters
        ----------
        snapshot_path : str
            The path to the snapshot file.
        """
        raise NotImplementedError("Publish method is not implemented")


class NullPublisher(Publisher):
    async def publish(self, snapshot_path: str) -> None:
        console.log(f"Mimic publishing to {snapshot_path}")
