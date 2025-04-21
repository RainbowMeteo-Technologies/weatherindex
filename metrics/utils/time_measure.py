import time

from typing import Any


class TimeMeasure:

    def __init__(self):
        self._t0 = time.time()

    def __call__(self, *args: Any, **kwds: Any) -> Any:
        return time.time() - self._t0

    def reset(self):
        self._t0 = time.time()
