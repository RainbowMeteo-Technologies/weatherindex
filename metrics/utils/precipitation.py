import metrics.utils.dbz as dbz
import numpy as np
import typing

from dataclasses import dataclass
from enum import IntEnum
from metrics.utils.dbz import dbz_to_precipitation_rate


class PrecipitationType(IntEnum):
    # All values should be less than 8
    # 0 - is reserved for non-type. This allows to create types array with np.zeros
    UNKNOWN = 0
    RAIN = 1
    SNOW = 2
    MIX = 3


RAIN_RATE_CONVERT_A: float = 200
RAIN_RATE_CONVERT_B: float = 1.6

SNOW_RATE_CONVERT_A: float = 200
SNOW_RATE_CONVERT_B: float = 2.0


@dataclass
class PrecipValue:
    dbz: typing.Optional[float]  # dbz value
    precip_type: PrecipitationType  # precipitation type

    def is_rain(self) -> bool:
        return self.precip_type == PrecipitationType.RAIN

    def to_mmh(self) -> typing.Optional[float]:

        if self.dbz is None:
            return None

        rain_mmh = dbz_to_precipitation_rate(dbz=self.dbz,
                                             a=RAIN_RATE_CONVERT_A,
                                             b=RAIN_RATE_CONVERT_B)
        snow_mmh = dbz_to_precipitation_rate(dbz=self.dbz,
                                             a=SNOW_RATE_CONVERT_A,
                                             b=SNOW_RATE_CONVERT_B)

        if self.precip_type == PrecipitationType.RAIN:
            return rain_mmh
        elif self.precip_type == PrecipitationType.SNOW:
            return snow_mmh
        elif self.precip_type == PrecipitationType.MIX:
            return max(rain_mmh, snow_mmh)

        return rain_mmh  # case of UNKNOWN precip type


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

    def get_point(self, py: int, px: int) -> PrecipValue:
        dbz = self.reflectivity[py, px]
        return PrecipValue(dbz=None if np.isnan(dbz) else dbz,
                           precip_type=PrecipitationType(self.type[py, px]))
