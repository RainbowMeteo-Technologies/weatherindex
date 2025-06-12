from abc import ABC, abstractmethod


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
