import numpy as np
import typing

from dataclasses import dataclass
from enum import IntEnum

import metrics.utils.dbz as dbz


class PrecipitationType(IntEnum):
    # All values should be less than 8
    # 0 - is reserved for non-type. This allows to create types array with np.zeros
    UNKNOWN = 0
    RAIN = 1
    SNOW = 2
    MIX = 3


@dataclass(frozen=True)
class PrecipitationData:
    """
    This class stores precipitation data of different types. Different precipitation data is
    accesible via properties.
    """
    # reflectivity data (dbz float values in range [-31, 95])
    reflectivity: np.ndarray
    # precipitation types mask (uint8 see PrecipitationType)
    type: np.ndarray

    def __post_init__(self):
        assert self.reflectivity.shape == self.type.shape
        assert self.reflectivity.dtype == np.float32
        assert self.type.dtype == np.uint8

        # TODO: use global flag to avoid these checks in production
        if not np.all(np.isnan(self.reflectivity)):  # avoid warning message. One of the value should not be NaN
            assert np.nanmin(self.reflectivity) >= dbz.MIN_VALUE
            assert np.nanmax(self.reflectivity) <= dbz.MAX_VALUE

    def __eq__(self, other: "PrecipitationData") -> bool:
        return np.array_equal(self.reflectivity, other.reflectivity, equal_nan=True) and \
            np.array_equal(self.type, other.type, equal_nan=True)

    def get(self, mask: typing.Union[PrecipitationType, typing.Iterable[PrecipitationType]]) -> np.ndarray:
        """Returns reflectivity by specified types mask
        """
        if isinstance(mask, PrecipitationType):
            mask = [mask]

        bit_mask = 0
        for value in mask:
            assert isinstance(value, PrecipitationType)
            assert value > 0  # 0 - is reserved value

            bit_mask = bit_mask | (1 << (value - 1))

        data_mask = np.bitwise_and(bit_mask, self.type)
        return np.where(data_mask, self.reflectivity, np.nan)

    @property
    def is_empty(self) -> bool:
        return np.all(np.isnan(self.reflectivity))
