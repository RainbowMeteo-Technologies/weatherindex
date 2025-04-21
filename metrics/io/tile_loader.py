from abc import abstractmethod
from metrics.utils.precipitation import PrecipitationData


class BaseTileLoader:

    @abstractmethod
    def load(self, offset: int, tile_x: int, tile_y: int) -> PrecipitationData:
        """Loads tile with specified offset in minutes
        Parameters
        ----------
        offset : int
            Time offset in minutes 0, 10, ...
        tile_x : int
            X coordinate of tile
        tile_y : int
            Y coordinate of tile

        Returns
        -------
        PrecipitationData
            Loaded precipitation data
        """
        raise NotImplementedError(f"Have to be overriden in {self.__class__.__name__}")
