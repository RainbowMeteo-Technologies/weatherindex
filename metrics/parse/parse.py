import os

from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from functools import partial
from metrics.data_vendor import BaseDataVendor, DataVendor
from metrics.parse import PROVIDERS_PARSERS
from metrics.parse.base_parser import BaseParser
from metrics.session import Session
from rich.console import Console
from rich.progress import track
from typing import Any, Callable, Dict, List, Optional


console = Console()


@dataclass
class ParseSource:
    vendor: str                 # name of the vendor
    input_folder: str           # path to the input folder
    output_folder: str          # path to the output folder
    parser_class: Any           # parser class
    session_path: str


@dataclass
class ParseJob:
    input_archive_path: str     # path to the input archive file
    output_parquet_path: str    # path to the output parquet file
    parser_class: Any           # parser class
    session_path: str


def _parse_process_impl(params: ParseJob) -> bool:
    try:

        parser: BaseParser = params.parser_class()
        parser.parse(input_archive_path=params.input_archive_path,
                     output_parquet_path=params.output_parquet_path)
        return True

    except Exception:
        console.print_exception()

    return False


def _collect_parse_jobs(source: ParseSource) -> List[Callable[[], bool]]:

    collected_archives = []
    for root, _, files in os.walk(source.input_folder):
        for file in files:
            if file.endswith(".zip"):
                collected_archives.append(os.path.join(root, file))

    if len(collected_archives) == 0:
        console.log(f"No source file for {source.vendor} was found for session {source.session_path}")
        return []

    console.log(f"Collected {len(collected_archives)} source files for "
                f"{source.vendor} for session {source.session_path}")

    os.makedirs(source.output_folder, exist_ok=True)

    jobs = []

    for zip_path in collected_archives:
        file_name, _ = os.path.splitext(os.path.basename(zip_path))
        output_file = os.path.join(source.output_folder, f"{file_name}.parquet")

        if os.path.exists(output_file):
            continue

        jobs.append(ParseJob(input_archive_path=zip_path,
                             output_parquet_path=output_file,
                             parser_class=source.parser_class,
                             session_path=source.session_path))

    return [partial(_parse_process_impl, params=job) for job in jobs]


def collect_jobs(session_path: str,
                 providers: List[BaseDataVendor] = [v for v in DataVendor],
                 providers_parser: Dict[BaseDataVendor, BaseParser] = PROVIDERS_PARSERS) -> List[Callable[[], bool]]:
    session = Session.create_from_folder(session_path=session_path)
    output_folder = session.tables_folder

    os.makedirs(output_folder, exist_ok=True)

    convert_sources: List[ParseSource] = []
    for provider in providers:
        parser_cls = providers_parser.get(provider.value)
        if parser_cls is not None:
            input_path = os.path.join(session.data_folder, provider.value)
            output_path = os.path.join(session.tables_folder, provider.value)
            convert_sources.append(ParseSource(vendor=provider.name,
                                               input_folder=input_path,
                                               output_folder=output_path,
                                               parser_class=parser_cls,
                                               session_path=session_path))
        else:
            console.log(f"No parser class found for provider {provider}")

    jobs: List[Callable[[], bool]] = []

    for source in convert_sources:
        jobs.extend(_collect_parse_jobs(source=source))

    return jobs


def parse(session_path: str,
          process_num: Optional[int] = None,
          providers: List[BaseDataVendor] = [v for v in DataVendor],
          providers_parser: Dict[BaseDataVendor, BaseParser] = PROVIDERS_PARSERS):
    """Parses data into common parquet format

    Parameters
    ----------
    session_path : str
        Path to a session folder
    process_num : int | None
        Number of processes for multiprocessing
    """
    console.log(f"Run parse command for {session_path}")

    console.log(f"Start session from {session_path}")
    session = Session.create_from_folder(session_path=session_path)
    console.log(session)

    jobs = collect_jobs(session_path=session_path,
                        providers=providers,
                        providers_parser=providers_parser)

    with ProcessPoolExecutor(process_num) as executor:
        futures = [executor.submit(job) for job in jobs]
        for _ in track(as_completed(futures),
                       description=f"Parse sources for {session.session_name}",
                       total=len(futures)):
            pass
