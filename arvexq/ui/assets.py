from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"


def _safe_path(name: str) -> Path:
    path = (STATIC / name).resolve()
    root = STATIC.resolve()
    if path != root and root not in path.parents:
        raise ValueError("invalid asset path")
    return path


@lru_cache(maxsize=32)
def read_asset(name: str) -> str:
    if name == "app.js":
        names = json.loads(_safe_path("app_sources.json").read_text(encoding="utf-8"))
        return "\n".join(_safe_path(part).read_text(encoding="utf-8") for part in names)
    return _safe_path(name).read_text(encoding="utf-8")


@lru_cache(maxsize=32)
def read_binary_asset(name: str) -> bytes:
    return _safe_path(name).read_bytes()


def clear_asset_cache() -> None:
    read_asset.cache_clear()
    read_binary_asset.cache_clear()
