from abc import ABC, abstractmethod


class Publisher(ABC):

    @abstractmethod
    async def publish(self, publish_path: str, downloaded_file_path: str) -> None:
        """
        Publish data from the storage to the destination.

        Parameters
        ----------
        publish_path : str
            The path of the file on the destination.
        downloaded_file_path : str
            The path to the file that was downloaded.
        """
        pass
