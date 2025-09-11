from itertools import islice
from typing import Generator, TypeVar


T = TypeVar("T")


def batched(iterable: list[T], n: int) -> Generator[list[T], None, None]:
    """Batch data into lists of length n. The last batch may be shorter.
    batched("ABCDEFG", 3) --> ABC DEF G
    for use with python <3.12
    """
    if n < 1:
        raise ValueError("n must be at least one")
    it = iter(iterable)
    while batch := list(islice(it, n)):
        yield batch
