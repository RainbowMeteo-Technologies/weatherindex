import io
import pytest
import tempfile
import zipfile

from datetime import datetime, timedelta, timezone
from sensors.providers.provider import BaseProvider
from sensors.providers.uscrn import UscrnSource
from sensors.publishers.publisher import Publisher
from sensors.utils.memory_zip import MemoryZip
from unittest.mock import MagicMock, patch

BASE_URL = "https://www.ncei.noaa.gov/pub/data/uscrn/products/subhourly01"

# 2026-10-21 12:00 UTC
TIMESTAMP = int(datetime(2026, 10, 21, 12, tzinfo=timezone.utc).timestamp())


def _row(wban: str, utc: datetime, precipitation: float = 0.0) -> str:
    """One CRNS0101-05 row in the NCEI subhourly01 fixed-width layout (135 columns plus newline)."""
    lst = utc - timedelta(hours=6)
    fields = [f"{wban:>5}", f"{utc:%Y%m%d}", f"{utc:%H%M}", f"{lst:%Y%m%d}", f"{lst:%H%M}", f"{2.623:6.3f}",
              f"{-102.81:7.2f}", f"{30.62:7.2f}", f"{4.3:7.1f}", f"{precipitation:7.1f}", f"{0:6d}", "0",
              f"{4.0:7.1f}", "C", "0", f"{67:5d}", "0", f"{-99.0:7.3f}", f"{-9999.0:7.1f}", f"{1046:5d}", "0",
              f"{2.42:7.2f}", "0"]
    return " ".join(fields) + "\n"


def _listing(*file_names: str) -> bytes:
    links = "\n".join(f'<tr><td><a href="{name}">{name}</a></td><td>2026-10-21 11:42</td></tr>' for name in file_names)
    return f"<html><body><table>\n<tr><td><a href=\"/pub/data/uscrn/products/\">Parent Directory</a></td></tr>\n{links}\n</table></body></html>".encode()


class FakeNcei:
    """Routes `Http.get` calls to an in-memory NCEI tree and records them."""

    def __init__(self, files: dict[str, bytes], listings: dict[int, bytes], failing: set[str] = frozenset()):
        self.files = files
        self.listings = listings
        self.failing = failing
        self.calls: list[tuple[str, dict]] = []

    async def get(self, url: str, headers: dict = {}, retry_count: int = 5):
        self.calls.append((url, dict(headers)))
        path = url[len(BASE_URL) + 1:]
        year, _, name = path.partition("/")
        if name == "":
            return self.listings.get(int(year))
        if name in self.failing:
            return None
        data = self.files.get(name)
        if data is None:
            return None
        rng = headers.get("Range")
        if rng is not None:
            assert rng.startswith("bytes=-")
            return data[-int(rng[len("bytes=-"):]):]
        return data


@pytest.fixture
def publisher():
    return MagicMock(spec=Publisher)


@pytest.fixture
def download_path():
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


async def _run_fetch_job(client: UscrnSource, fake: FakeNcei, timestamp: int = TIMESTAMP) -> dict[str, bytes]:
    client._storage = MemoryZip()
    with patch("sensors.providers.uscrn.Http.get", side_effect=fake.get):
        await client.fetch_job(timestamp)
    client._storage.close()
    with zipfile.ZipFile(io.BytesIO(client._storage.buffer.getvalue())) as zf:
        return {name: zf.read(name) for name in zf.namelist()}


def test_fixture_row_matches_the_fixed_width_layout():
    assert len(_row("03047", datetime(2026, 10, 21, 11, 0))) == 136


def test_uscrn_is_an_hourly_provider(publisher, download_path):
    client = UscrnSource(publisher=publisher, download_path=download_path)

    assert isinstance(client, BaseProvider)
    assert client._service == "USCRN"
    assert client._frequency == 3600


@pytest.mark.asyncio
async def test_one_range_tail_request_per_listed_sensor(publisher, download_path):
    names = ["CRNS0101-05-2026-AK_Aleknagik_1_NNE.txt", "CRNS0101-05-2026-TX_Monahans_6_ENE.txt"]
    fake = FakeNcei(files={name: _row("03047", datetime(2026, 10, 21, 11, 0)).encode() for name in names},
                    listings={2026: _listing(*names)})
    client = UscrnSource(publisher=publisher, download_path=download_path)

    await _run_fetch_job(client, fake)

    sensor_calls = [(url, headers) for url, headers in fake.calls if url.endswith(".txt")]
    # 3 h of 5-minute rows (36) plus one row that is cut away, 136 bytes each
    assert sorted(sensor_calls) == sorted([(f"{BASE_URL}/2026/{name}", {"Range": "bytes=-5032"}) for name in names])


@pytest.mark.asyncio
async def test_snapshot_holds_complete_tail_lines_per_sensor_file(publisher, download_path):
    name = "CRNS0101-05-2026-TX_Monahans_6_ENE.txt"
    rows = [_row("03047", datetime(2026, 10, 21, 8, 0) + i * timedelta(minutes=5))
            for i in range(48)]
    content = "".join(rows).encode()
    fake = FakeNcei(files={name: content}, listings={2026: _listing(name)})
    client = UscrnSource(publisher=publisher, download_path=download_path)

    snapshot = await _run_fetch_job(client, fake)

    assert list(snapshot) == [name]
    stored = snapshot[name].decode().splitlines(keepends=True)
    # the 5032-byte tail starts in the middle of a row; only the complete rows after it are stored,
    # which still covers the last 3 h (36 rows)
    assert len(content) > 5032
    assert len(stored) >= 36
    assert stored == rows[-len(stored):]


@pytest.mark.asyncio
async def test_partial_last_line_is_not_stored(publisher, download_path):
    name = "CRNS0101-05-2026-TX_Monahans_6_ENE.txt"
    complete = _row("03047", datetime(2026, 10, 21, 11, 0)) + _row("03047", datetime(2026, 10, 21, 11, 5))
    content = (complete + "03047 2026102").encode()
    fake = FakeNcei(files={name: content}, listings={2026: _listing(name)})
    client = UscrnSource(publisher=publisher, download_path=download_path)

    snapshot = await _run_fetch_job(client, fake)

    # the file is shorter than the tail, so its first line is complete and kept
    assert snapshot[name].decode() == complete


class RaisingNcei(FakeNcei):
    async def get(self, url: str, headers: dict = {}, retry_count: int = 5):
        if url.endswith("AL_Fairhope_3_NE.txt"):
            self.calls.append((url, dict(headers)))
            raise RuntimeError("connection reset")
        return await super().get(url, headers, retry_count)


@pytest.mark.asyncio
async def test_failing_sensor_does_not_abort_the_others(publisher, download_path, caplog):
    ok = "CRNS0101-05-2026-TX_Monahans_6_ENE.txt"
    unavailable = "CRNS0101-05-2026-AK_Aleknagik_1_NNE.txt"
    raising = "CRNS0101-05-2026-AL_Fairhope_3_NE.txt"
    row = _row("03047", datetime(2026, 10, 21, 11, 0))
    fake = RaisingNcei(files={ok: row.encode(), raising: row.encode(), unavailable: row.encode()},
                       listings={2026: _listing(ok, unavailable, raising)},
                       failing={unavailable})
    client = UscrnSource(publisher=publisher, download_path=download_path)

    snapshot = await _run_fetch_job(client, fake)

    assert snapshot == {ok: row.encode()}
    assert unavailable in caplog.text
    assert raising in caplog.text


@pytest.mark.asyncio
async def test_year_rollover_includes_previous_year_files(publisher, download_path):
    old = "CRNS0101-05-2026-TX_Monahans_6_ENE.txt"
    new = "CRNS0101-05-2027-TX_Monahans_6_ENE.txt"
    old_row = _row("03047", datetime(2026, 12, 31, 23, 55))
    new_row = _row("03047", datetime(2027, 1, 1, 1, 0))
    fake = FakeNcei(files={old: old_row.encode(), new: new_row.encode()},
                    listings={2026: _listing(old), 2027: _listing(new)})
    client = UscrnSource(publisher=publisher, download_path=download_path)

    snapshot = await _run_fetch_job(client, fake, int(datetime(2027, 1, 1, 2, tzinfo=timezone.utc).timestamp()))

    assert snapshot == {old: old_row.encode(), new: new_row.encode()}


@pytest.mark.asyncio
async def test_missing_new_year_directory_keeps_previous_year_files(publisher, download_path):
    old = "CRNS0101-05-2026-TX_Monahans_6_ENE.txt"
    old_row = _row("03047", datetime(2026, 12, 31, 23, 55))
    fake = FakeNcei(files={old: old_row.encode()}, listings={2026: _listing(old)})
    client = UscrnSource(publisher=publisher, download_path=download_path)

    snapshot = await _run_fetch_job(client, fake, int(datetime(2027, 1, 1, 0, tzinfo=timezone.utc).timestamp()))

    assert snapshot == {old: old_row.encode()}


@pytest.mark.asyncio
async def test_previous_year_is_not_listed_mid_year(publisher, download_path):
    fake = FakeNcei(files={}, listings={2026: _listing()})
    client = UscrnSource(publisher=publisher, download_path=download_path)

    await _run_fetch_job(client, fake)

    assert [url for url, _ in fake.calls] == [f"{BASE_URL}/2026/"]
