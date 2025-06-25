import os
import multiprocessing

from dataclasses import dataclass

from metrics.data_vendor import BaseDataVendor, DataVendor
from metrics.parse import PROVIDERS_PARSERS
from metrics.parse.base_parser import BaseParser
from metrics.session import Session

from rich.console import Console
from rich.progress import track

from typing import Any, Dict, Optional, List, Tuple, Type

console = Console()


@dataclass
class ParseSource:
    vendor: str                 # name of the vendor
    input_folder: str           # path to the input folder
    output_folder: str          # path to the output folder
    parser_class: Any           # parser class


@dataclass
class ParseJob:
    input_archive_path: str     # path to the input archive file
    output_parquet_path: str    # path to the output parquet file
    parser_class: Any           # parser class


def _parse_process_impl(parse_job: ParseJob):
    parser: BaseParser = parse_job.parser_class()
    parser.parse(input_archive_path=parse_job.input_archive_path,
                 output_parquet_path=parse_job.output_parquet_path)


def _execute_source_jobs(source_name: str,
                         jobs: List[ParseJob],
                         process_num: int):
    with multiprocessing.Pool(processes=process_num) as pool:
        for _ in track(pool.imap_unordered(_parse_process_impl, jobs),
                       total=len(jobs),
                       description=f"Parse {source_name}"):
            pass


def _process_source(source: ParseSource, process_num: int):
    # collect archives
    collected_archives = []
    for root, _, files in os.walk(source.input_folder):
        for file in files:
            if file.endswith(".zip"):
                collected_archives.append(os.path.join(root, file))

        os.makedirs(source.output_folder, exist_ok=True)
        if len(collected_archives) > 0:
            jobs = []
            for zip_path in collected_archives:
                file_name, _ = os.path.splitext(os.path.basename(zip_path))
                output_file = os.path.join(source.output_folder, f"{file_name}.parquet")

                if os.path.exists(output_file):
                    continue

                jobs.append(ParseJob(input_archive_path=zip_path,
                                     output_parquet_path=output_file,
                                     parser_class=source.parser_class))

            _execute_source_jobs(source_name=source.vendor,
                                 jobs=jobs,
                                 process_num=process_num)


def parse(session_path: str,
          process_num: Optional[int],
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
                                               parser_class=parser_cls))
        else:
            console.log(f"No parser class found for provider {provider}")

    for source in convert_sources:
        _process_source(source=source,
                        process_num=process_num)
