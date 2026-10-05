from __future__ import annotations

from functools import lru_cache
from pathlib import Path

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"


@lru_cache(maxsize=16)
def read_asset(name: str) -> str:
    path = (STATIC / name).resolve()
    if STATIC.resolve() not in path.parents:
        raise ValueError("invalid asset path")
    return path.read_text(encoding="utf-8")


def clear_asset_cache() -> None:
    read_asset.cache_clear()
