import numpy as np
import os
import pytest

import metrics.io.rainviewer as rainviewer
import metrics.utils.precipitation as precip

SCRIPT_DIRECTORY = os.path.dirname(os.path.realpath(__file__))


class TestRainviewerIO:

    @pytest.mark.parametrize("shape", [
        (1, 1),
        (2, 2, 1),
        (3, 3, 2),
        (5, 5, 3),
        (7, 7, 5),
        (12, 12, 7, 5)
    ])
    def test_invald_data_shape(self, shape):
        with pytest.raises(AssertionError):
            rainviewer.decode_data_from_image(np.zeros(shape, dtype=np.float32))

    @pytest.mark.parametrize("in_type", [
        np.uint16, np.uint32, np.uint64, np.float16, np.float64
    ])
    def test_invald_data_type(self, in_type):
        with pytest.raises(AssertionError):
            rainviewer.decode_data_from_image(np.zeros((5, 5), dtype=in_type))

    def test_decode_image_no_data(self):

        image = np.zeros((4, 4, 4), dtype=np.uint8)

        image[0, :] = (0, 0, 0, 255)
        image[1, :] = (0, 0, 0, 254)
        image[2, :] = (128, 128, 128, 0)  # snow -32 dBZ
        image[3, :] = (128, 128, 128, 255)

        result = rainviewer.decode_data_from_image(image)

        assert result.reflectivity.dtype == np.float32
        assert result.type.dtype == np.uint8
        assert np.all(np.isnan(result.reflectivity))

    def test_decode_data_values(self):

        image = np.zeros((10, 10, 4), dtype=np.uint8)

        # rain
        image[0, :] = (10, 10, 10, 255)
        image[1, :] = (40, 40, 40, 255)  # dbz = 8
        image[2, :] = (41, 41, 41, 255)  # dbz = 9
        image[3, :] = (42, 42, 42, 255)  # dbz = 10
        image[4, :] = (127, 127, 127, 255)  # dbz = 95

        # snow
        image[5, :] = (138, 138, 138, 255)
        image[6, :] = (168, 168, 168, 255)  # dbz = 8
        image[7, :] = (169, 169, 169, 255)  # dbz = 9
        image[8, :] = (180, 180, 180, 255)  # dbz = 20
        image[9, :] = (255, 255, 255, 255)  # dbz = 95

        result = rainviewer.decode_data_from_image(image)
        refl = result.reflectivity

        assert result.type.dtype == np.uint8

        # rain
        assert np.all(result.type[:5, :] ==
                      precip.PrecipitationType.RAIN)
        assert np.all(refl[0, :] == -22.0)
        assert np.all(refl[1, :] == 8.0)
        assert np.all(refl[2, :] == 9.0)
        assert np.all(refl[3, :] == 10.0)
        assert np.all(refl[4, :] == 95.0)

        # snow
        assert np.all(result.type[5:, :] ==
                      precip.PrecipitationType.SNOW)
        assert np.all(refl[5, :] == -22.0)
        assert np.all(refl[6, :] == 8.0)
        assert np.all(refl[7, :] == 9.0)
        assert np.all(refl[8, :] == 20.0)
        assert np.all(refl[9, :] == 95.0)

    def test_encode_data(self):

        image = np.zeros((256, 256, 4), dtype=np.uint8)

        for i in range(256):
            image[i, :, :3] = i

        image[:, :128, 3] = 0
        image[:, 128:, 3] = 255

        # make reverse test
        decoded = rainviewer.decode_data_from_image(image)
        encoded = rainviewer.encode_data_to_image(decoded)

        assert np.all(encoded[..., :3] == image[..., :3])

    @pytest.mark.parametrize("shape", [
        (12,),
        (12, 12, 5),
        (12, 12, 7, 5),
    ])
    def test_encode_data_invalid_shape(self, shape):
        with pytest.raises(AssertionError):
            data = precip.PrecipitationData(
                reflectivity=np.zeros(shape, dtype=np.float32),
                type=np.zeros(shape, dtype=np.uint8))

            rainviewer.encode_data_to_image(data)

    @pytest.mark.parametrize("refl_type,type_type", [
        (np.float32, np.uint32),
        (np.float16, np.uint8),
        (np.float64, np.uint64)
    ])
    def test_encode_data_invalid_types(self, refl_type, type_type):
        with pytest.raises(AssertionError):
            data = precip.PrecipitationData(
                reflectivity=np.zeros((5, 5), dtype=refl_type),
                type=np.zeros((5, 5), dtype=type_type))

            rainviewer.encode_data_to_image(data)

    def test_decode_mask(self):
        with open(os.path.join(SCRIPT_DIRECTORY, "rainviewer_mask.png"), "rb") as file:
            mask = rainviewer.decode_mask_from_file(file)

        assert isinstance(mask, np.ndarray)

        assert mask[-1, 0]  # left bottom corner
        assert mask[-1, -1]  # right bottom corner

        assert not mask[0, 0]  # left top corner
        assert not mask[0, -1]  # right top corner

    def test_decode_mask_data(self):
        mask_fo = open(os.path.join(SCRIPT_DIRECTORY, "rainviewer_mask.png"), "rb")
        data_fo = open(os.path.join(SCRIPT_DIRECTORY, "rainviewer_data.png"), "rb")

        data = rainviewer.decode_data_from_file(data_fo, mask_fo)

        assert not np.isnan(data.reflectivity[-1, 0])  # left bottom corner
        assert not np.isnan(data.reflectivity[-1, -1])  # right bottom corner

        assert np.isnan(data.reflectivity[0, 0])  # left top corner
        assert np.isnan(data.reflectivity[0, -1])  # right top corner

        mask_fo.close()
        data_fo.close()
