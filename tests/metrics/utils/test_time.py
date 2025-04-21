import pytest

from metrics.utils.time import floor_timestamp


class TestTime:

    @pytest.mark.parametrize("timestamp, period, expected_timestamp", [
        (1, 1, 1),
        (3700, 2600, 2600),
        (3699, 3700, 0)
    ])
    def test_floor_timestamp(self, timestamp: int, period: int, expected_timestamp: int):
        assert floor_timestamp(timestamp=timestamp, period=period) == expected_timestamp
