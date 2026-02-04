import pytest

from metrics.utils.precipitation import PrecipValue, PrecipitationType


class TestPrecipValue:

    @pytest.mark.parametrize("precip_type, dbz, expected_precipitation_rate", [
        (PrecipitationType.RAIN, 10, 0.153765),
        (PrecipitationType.SNOW, 10, 0.223606),
        (PrecipitationType.MIX, 10, 0.223606),
    ])
    def test_dbz_to_precipitation_rate(self,
                                       precip_type: PrecipitationType,
                                       dbz: float,
                                       expected_precipitation_rate: float):

        precip_value = PrecipValue(dbz=dbz, precip_type=precip_type)

        approx_precip_rate = pytest.approx(precip_value.to_mmh(), abs=1e-6)
        assert approx_precip_rate == expected_precipitation_rate
