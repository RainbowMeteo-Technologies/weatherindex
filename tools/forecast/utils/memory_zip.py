import zipfile

from io import BytesIO


class MemoryZip:
    """
    MemoryZip is a class that allows to store data in a zip file in memory.
    """

    def __init__(self):
        self._buffer = BytesIO()
        self._zf = zipfile.ZipFile(self._buffer, mode="w", compression=zipfile.ZIP_DEFLATED)

    @property
    def buffer(self) -> BytesIO:
        return self._buffer

    def write_raw(self, file_path: str, data: str | bytes):
        """
        Write raw data to the zip file.

        Parameters
        ----------
        file_path : str
            The path to the data in the zip file.
        data : str | bytes
            The data to write to the zip file.
        """
        self._zf.writestr(file_path, data)

    def close(self):
        """
        Close the zip file.
        """
        self._zf.close()
