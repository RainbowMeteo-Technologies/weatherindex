import math
import pytest

from metrics.utils.dbz import dbz_to_precipitation_rate


@pytest.mark.parametrize("dbz,a,b,expected", [
    (20, 200, 1.6, 0.648419),
    (50, 200, 1.6, 48.624624),
])
def test_dbz_to_precipitation_rate(dbz, a, b, expected):
    assert math.isclose(dbz_to_precipitation_rate(dbz=dbz, a=a, b=b), expected, abs_tol=1e-6)
