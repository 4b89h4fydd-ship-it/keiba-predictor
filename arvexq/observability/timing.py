from __future__ import annotations

from contextlib import contextmanager
from time import perf_counter
from typing import Iterator


@contextmanager
def timed(bucket: dict[str, float], key: str) -> Iterator[None]:
    start = perf_counter()
    try:
        yield
    finally:
        bucket[key] = round((perf_counter() - start) * 1000.0, 2)
