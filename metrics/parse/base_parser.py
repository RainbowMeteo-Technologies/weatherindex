import os
import pandas
import typing
import zipfile

from abc import abstractmethod


class BaseParser:
    """Base class for raw observation/forecast parsing"""

    def parse(self, input_archive_path: str, output_parquet_path: str):
        """Converts data from raw format to parquet table

        Parameters
        ----------
        input_archive_path : str
            Path to the input archive file
        output_parquet_path : str
            Path to the output parquet file
        """
        rows = []
        with zipfile.ZipFile(input_archive_path, "r") as zip_file:
            zip_name = os.path.basename(input_archive_path)
            timestamp = int(zip_name.replace(".zip", ""))

            for file_name in zip_file.namelist():
                _, ext = os.path.splitext(file_name)
                if self._should_parse_file_extension(ext):
                    parsed_rows = self._parse_impl(timestamp=timestamp,
                                                   file_name=file_name,
                                                   data=zip_file.read(file_name))
                    rows.extend(parsed_rows)

        data_frame = pandas.DataFrame(rows, columns=self._get_columns())
        data_frame.to_parquet(output_parquet_path, compression="gzip")

    @abstractmethod
    def _parse_impl(self, timestamp: int, file_name: str, data: bytes) -> typing.List[typing.List[any]]:
        """Converts data from raw format to parquet table

        Parameters
        ----------
        timestamp : int
            Timestamp of the archive
        file_name : str
            Name of the file from archive
        data : bytes
            Data to parse

        Returns
        -------
        List[List[any]]
            Retruns list of parsed rows. Items of each row have to be in the same order as `_get_columns` values
        """
        raise NotImplementedError(f"This method have to be overriden in class {self.__class__.__name__}")

    @abstractmethod
    def _should_parse_file_extension(self, file_extension: str) -> bool:
        """Checks is file with specified extension should be parsed

        Parameters
        ----------
        file_extension : str
            File extension in format `.ext`

        Returns
        -------
        bool
            Returns `True` if file have to be parsed, otherwise returns `False`
        """
        raise NotImplementedError(f"This method have to be overriden in class {self.__class__.__name__}")

    @abstractmethod
    def _get_columns(self) -> typing.List[str]:
        """Returns list of columns in the final parquet file

        Returns
        -------
        List[str]
            Returns list of columns
        """
        raise NotImplementedError(f"This method have to be overriden in class {self.__class__.__name__}")


class RawParser(BaseParser):
    """Base class of the parsers split into the raw parsing of a file and the thresholds applied to its rows.

    `parse_raw` returns the rows as the provider gives them, in the order of `_get_columns`; `apply_thresholds`
    changes rows by the rules of the main pipeline (by default none). `_parse_impl` is their composition, so the output
    of the parsing stays the same, while a consumer needing the raw values calls `parse_raw`.
    """

    def parse_raw(self, timestamp: int, file_name: str, data: bytes) -> typing.List[typing.List[any]]:
        """Converts the raw data of a file to rows without applying thresholds, see `BaseParser._parse_impl`"""
        raise NotImplementedError(f"This method have to be overriden in class {self.__class__.__name__}")

    def apply_thresholds(self, rows: typing.List[typing.List[any]]) -> typing.List[typing.List[any]]:
        """Applies the thresholds of the main pipeline to the rows of `parse_raw`; no thresholds by default"""
        return rows

    def _parse_impl(self, timestamp: int, file_name: str, data: bytes) -> typing.List[typing.List[any]]:
        """See :func:`~metrics.base_parser.BaseParser._parse_impl`"""
        return self.apply_thresholds(self.parse_raw(timestamp=timestamp, file_name=file_name, data=data))
