
import cv2
import functools
import numpy as np
import os
import typing
import zipfile

from metrics.io.tile_loader import BaseTileLoader
from metrics.utils.dbz import MIN_VALUE
from metrics.utils.precipitation import PrecipitationData, PrecipitationType


def decode_data_from_image(image: np.ndarray) -> PrecipitationData:
    """
    Decodes precipitation data from an image. Algorithm implemented according to the
    [documentation](https://www.rainviewer.com/ua/ru/api/color-schemes.html#dbzMatrix)

    Parameters
    ----------
    image : np.ndarray
        BGRA Image to decode

    Returns
    -------
    PrecipitationData
        Returns decoded precipitation data
    """
    assert len(image.shape) == 3
    assert image.shape[2] == 4
    assert image.dtype == np.uint8

    red_channel = image[:, :, 0]
    # equal to image[:, :, 0] % 128 (remove high bit)
    raw_data = (red_channel & 127)
    dbz = raw_data.astype(np.float32) - 32

    reflectivity = np.where(raw_data > 0, dbz, np.nan)
    type = np.where(red_channel > 127,
                    np.uint8(PrecipitationType.SNOW),
                    np.uint8(PrecipitationType.RAIN))

    return PrecipitationData(reflectivity=reflectivity,
                             type=type)


def decode_data_from_file(data_fo: typing.BinaryIO,
                          mask_fo: typing.Optional[typing.BinaryIO] = None) -> typing.Optional[PrecipitationData]:
    """
    Loads rainviewer tile from file and decode it

    Parameters
    ----------
    data_fo : BinaryIO
        File-like object that contains data layer

    maks_fo : Optional[BinaryIO]
        File-like object that contains coverage mask

    Returns
    -------
    PrecipitationData
        Returns loaded and decoded precipitation data. If wasn't able to load data, then returns None
    """
    image = cv2.imdecode(np.asarray(bytearray(data_fo.read()), dtype=np.uint8),
                         cv2.IMREAD_UNCHANGED)

    if len(image.shape) == 2:
        assert image.min() == 0
        assert image.max() == 0
        return None  # rainviewer returns empty tile

    data = decode_data_from_image(image=image)
    if mask_fo:
        mask = decode_mask_from_file(mask_fo)
        reflectivity = np.where(np.isnan(data.reflectivity), MIN_VALUE, data.reflectivity)
        reflectivity = np.where(mask, reflectivity, np.nan)

        data = PrecipitationData(reflectivity=reflectivity, type=data.type)

    return data


def encode_data_to_image(precipitation: PrecipitationData) -> np.ndarray:
    """
    Encodes precipitation data into rainviewer image format. This is a reverse function for `decode_image`

    Parameters
    ----------
    precipitation : PrecipitationData
        Data to encode into an image. Reflectivity should be in range [-32; 95]. Values outside this range will be clamped

    Returns
    -------
    np.ndarray
        Returns encoded BGRA image
    """
    assert len(precipitation.reflectivity.shape) == 2
    assert precipitation.reflectivity.dtype == np.float32
    assert precipitation.type.dtype == np.uint8

    nan_mask = np.isnan(precipitation.reflectivity)
    refl = np.where(nan_mask, -32, precipitation.reflectivity)
    rain_value = np.clip(refl, -32, 95) + 32.0
    rain_value = rain_value.astype(np.uint8)
    snow_value = rain_value + 128
    channel_value = np.where(precipitation.type == PrecipitationType.SNOW,
                             snow_value,
                             rain_value)

    height, width = precipitation.reflectivity.shape

    image = np.zeros((height, width, 4), dtype=np.uint8)
    image[..., 0] = channel_value
    image[..., 1] = channel_value
    image[..., 2] = channel_value
    image[..., 3] = np.where(nan_mask, 0, 255)

    return image


def decode_mask_from_file(fo: typing.BinaryIO) -> np.ndarray:
    """
    Loads rainviewer coverage mask from file and decode it

    Parameters
    ----------
    fo : BinaryIO
        file-like object

    Returns
    -------
    np.ndarray
        Returns loaded boolean mask from a file. Where pixels covered by radar is marked with `True` value
    """
    image = cv2.imdecode(np.asarray(bytearray(fo.read()), dtype=np.uint8),
                         cv2.IMREAD_UNCHANGED)

    assert len(image.shape) == 3
    assert image.shape[2] == 4

    return image[..., 3] == 0


class RainViewerTileLoader(BaseTileLoader):

    ZOOM_LEVEL = 7

    def __init__(self, zip_path: str) -> None:
        self._zip_file = zipfile.ZipFile(zip_path, "r")

        file_name = os.path.basename(zip_path)
        self._timestamp_path, _ = os.path.splitext(file_name)

        self._zip_precip_type = None

    def load(self, offset: int, tile_x: int, tile_y: int) -> PrecipitationData:
        """Overriden from base class"""
        return self._load_impl(offset=offset, tile_x=tile_x, tile_y=tile_y)

    @functools.lru_cache(maxsize=1024, typed=False)
    def _load_impl(self, offset: int, tile_x: int, tile_y: int) -> PrecipitationData:
        try:
            tile_path = os.path.join(self._timestamp_path, "_map", f"t{offset}",
                                     str(RainViewerTileLoader.ZOOM_LEVEL), str(tile_x), f"{tile_y}.png")
            mask_path = os.path.join(self._timestamp_path, "_mask",
                                     str(RainViewerTileLoader.ZOOM_LEVEL), str(tile_x), f"{tile_y}.png")

            with self._zip_file.open(tile_path, "r") as tile_file:
                with self._zip_file.open(mask_path, "r") as mask_file:
                    return decode_data_from_file(tile_file, mask_file)

        except KeyError:
            return None  # no file in the archive
