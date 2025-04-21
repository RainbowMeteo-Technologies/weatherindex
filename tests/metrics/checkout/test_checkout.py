import pytest
import typing

from metrics.checkout.checkout import _build_snapshot_list, _build_s3_download_list


class TestCheckout:

    @pytest.mark.parametrize("start_time, end_time, period, expected_list", [
        (0, 1800, 600, [0, 600, 1200, 1800]),
        (50, 110, 30, [30, 60, 90, 120])
    ])
    def test_build_snapshot_list(self, start_time: int, end_time: int, period: int, expected_list: typing.List[int]):
        built_list = _build_snapshot_list(
            start_time=start_time,
            end_time=end_time,
            period=period)

        assert built_list == expected_list

    @pytest.mark.parametrize("start_time, end_time, period, expected_error", [
        (-1, 10, 10, AssertionError),  # start is negative
        (10, 5, 10, AssertionError),  # end < start
        (10, 20, 0, AssertionError),  # invalid period
        (10, 20, -10, AssertionError),  # invalid period
    ])
    def test_build_snapshot_list_error(self, start_time: int, end_time: int, period: int, expected_error: any):
        with pytest.raises(expected_exception=expected_error):
            _build_snapshot_list(
                start_time=start_time,
                end_time=end_time,
                period=period)

    @pytest.mark.parametrize("snaphots, s3_uri, rule, expected_uris", [
        ([234, 567, 987], "s3://rainbow-test/", "timestamp",
         ["s3://rainbow-test/234.zip",
          "s3://rainbow-test/567.zip",
          "s3://rainbow-test/987.zip"
          ]),
        ([0], "s3://rainbow-test/zero/", "timestamp", ["s3://rainbow-test/zero/0.zip"]),
        ([], "s3://rainbow-test/", "timestamp", []),
    ])
    def test_build_s3_download_list(
            self,
            snaphots: typing.List[int],
            s3_uri: str,
            rule: str,
            expected_uris: typing.List[str]):
        uris = _build_s3_download_list(snaphots=snaphots, s3_uri=s3_uri, rule=rule)
        assert uris == expected_uris
