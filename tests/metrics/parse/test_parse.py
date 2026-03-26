import os
import pytest

from metrics.parse import parse
from unittest.mock import MagicMock, patch


class FailingMock(MagicMock):
    def __getattr__(self, name):
        attr = super().__getattr__(name)
        if callable(attr):
            attr.side_effect = Exception(f"{name} failed")
        return attr


@pytest.mark.parametrize("parser_class, expected_result", [
    (
        # parser_class
        MagicMock(return_value=MagicMock()),
        # expected_result
        True
    ),
    (
        # parser_class
        MagicMock(side_effect=Exception("Failed")),
        # expected_result
        False
    ),
    (
        # parser_class
        MagicMock(return_value=FailingMock()),
        # expected_result
        False
    ),
])
def test_parse_process_impl(parser_class, expected_result):

    parse_job = parse.ParseJob(input_archive_path="/session/data/input.zip",
                               output_parquet_path="/session/tables/output.parquet",
                               parser_class=parser_class,
                               session_path="/session")

    result = parse._parse_process_impl(parse_job)

    assert result is expected_result


@pytest.fixture
def parse_source(tmp_path):
    return parse.ParseSource(vendor="test_vendor",
                             input_folder=str(tmp_path / "input"),
                             output_folder=str(tmp_path / "output"),
                             parser_class=MagicMock,
                             session_path="/session",)


def test_collect_parse_jobs_no_zips(parse_source, tmp_path):
    os.makedirs(parse_source.input_folder)
    result = parse._collect_parse_jobs(parse_source)
    assert result == []


def test_collect_parse_jobs_returns_jobs_for_zips(parse_source, tmp_path):
    os.makedirs(parse_source.input_folder)
    (tmp_path / "input" / "file1.zip").touch()
    (tmp_path / "input" / "file2.zip").touch()

    result = parse._collect_parse_jobs(parse_source)

    assert len(result) == 2


def test_collect_parse_jobs_skips_existing_parquet(parse_source, tmp_path):
    os.makedirs(parse_source.input_folder)
    os.makedirs(parse_source.output_folder)
    (tmp_path / "input" / "file1.zip").touch()
    (tmp_path / "output" / "file1.parquet").touch()

    result = parse._collect_parse_jobs(parse_source)

    assert result == []


def test_collect_parse_jobs_skips_non_zip_files(parse_source, tmp_path):
    os.makedirs(parse_source.input_folder)
    (tmp_path / "input" / "file1.csv").touch()
    (tmp_path / "input" / "file2.txt").touch()

    result = parse._collect_parse_jobs(parse_source)

    assert result == []


def test_collect_parse_jobs_creates_output_folder(parse_source, tmp_path):
    os.makedirs(parse_source.input_folder)
    (tmp_path / "input" / "file1.zip").touch()

    assert not os.path.exists(parse_source.output_folder)
    parse._collect_parse_jobs(parse_source)
    assert os.path.exists(parse_source.output_folder)


def test_collect_parse_jobs_no_output_folder_if_no_zips(parse_source, tmp_path):
    os.makedirs(parse_source.input_folder)

    parse._collect_parse_jobs(parse_source)

    assert not os.path.exists(parse_source.output_folder)


def test_collect_parse_jobs_walks_subdirectories(parse_source, tmp_path):
    subdir = tmp_path / "input" / "sub"
    os.makedirs(subdir)
    (subdir / "file1.zip").touch()

    result = parse._collect_parse_jobs(parse_source)

    assert len(result) == 1


@pytest.fixture
def mock_session(tmp_path):
    session = MagicMock()
    session.tables_folder = str(tmp_path / "tables")
    session.data_folder = str(tmp_path / "data")
    return session


@pytest.fixture
def mock_providers():
    p1, p2 = MagicMock(), MagicMock()
    p1.value = "vendor1"
    p1.name = "Vendor1"
    p2.value = "vendor2"
    p2.name = "Vendor2"
    return [p1, p2]


@pytest.fixture
def mock_parsers(mock_providers):
    return {p.value: MagicMock() for p in mock_providers}


@patch("metrics.parse.parse.Session")
@patch("metrics.parse.parse._collect_parse_jobs", return_value=[])
def test_collect_jobs_creates_tables_folder(mock_collect,
                                            mock_session_cls,
                                            mock_session,
                                            mock_providers,
                                            mock_parsers,
                                            tmp_path):
    mock_session_cls.create_from_folder.return_value = mock_session

    parse.collect_jobs(session_path="/session", providers=mock_providers, providers_parser=mock_parsers)

    assert os.path.exists(mock_session.tables_folder)


@patch("metrics.parse.parse.Session")
@patch("metrics.parse.parse._collect_parse_jobs", return_value=[MagicMock()])
def test_collect_jobs_returns_jobs(mock_collect, mock_session_cls, mock_session, mock_providers, mock_parsers):
    mock_session_cls.create_from_folder.return_value = mock_session

    result = parse.collect_jobs(session_path="/session", providers=mock_providers, providers_parser=mock_parsers)

    assert len(result) == len(mock_providers)


@patch("metrics.parse.parse.Session")
@patch("metrics.parse.parse._collect_parse_jobs", return_value=[])
def test_collect_jobs_skips_provider_without_parser(mock_collect, mock_session_cls, mock_session, mock_providers):
    mock_session_cls.create_from_folder.return_value = mock_session

    result = parse.collect_jobs(session_path="/session", providers=mock_providers, providers_parser={})

    assert result == []


@patch("metrics.parse.parse.Session")
@patch("metrics.parse.parse._collect_parse_jobs", return_value=[])
def test_collect_jobs_passes_correct_paths_to_source(mock_collect,
                                                     mock_session_cls,
                                                     mock_session,
                                                     mock_providers,
                                                     mock_parsers,
                                                     tmp_path):
    mock_session_cls.create_from_folder.return_value = mock_session

    parse.collect_jobs(session_path="/session", providers=mock_providers, providers_parser=mock_parsers)

    for call_args in mock_collect.call_args_list:
        source = call_args.kwargs["source"]
        assert source.input_folder.startswith(mock_session.data_folder)
        assert source.output_folder.startswith(mock_session.tables_folder)
