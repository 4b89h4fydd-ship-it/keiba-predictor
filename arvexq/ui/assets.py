from __future__ import annotations

from functools import lru_cache
from pathlib import Path

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"

# Runtime assembly uses the responsibility-owned script; the original static file
# remains an exact-byte compatibility snapshot for existing public asset routes.
_COMPONENT_SCRIPT_OWNERS = {
    "history/temporal.js": 58,
    "history/view.js": 182,
    "forecast/prediction_frame.js": 185,
    "forecast/mark_frame.js": 186,
    "forecast/ticket_frame.js": 187,
}


def _safe_path(name: str) -> Path:
    path = (STATIC / name).resolve()
    root = STATIC.resolve()
    if path != root and root not in path.parents:
        raise ValueError("invalid asset path")
    return path


@lru_cache(maxsize=32)
def read_asset(name: str) -> str:
    source_path = _safe_path(name)
    owner = _COMPONENT_SCRIPT_OWNERS.get(name)
    if owner is None:
        return source_path.read_text(encoding="utf-8")
    from arvexq.components.runtime import component_path
    canonical_path = component_path(owner) / "ui" / source_path.name
    original = source_path.read_bytes()
    migrated = canonical_path.read_bytes()
    if migrated != original:
        raise ValueError(f"component UI script changed: {name}")
    return migrated.decode("utf-8")


@lru_cache(maxsize=32)
def read_binary_asset(name: str) -> bytes:
    return _safe_path(name).read_bytes()


def clear_asset_cache() -> None:
    read_asset.cache_clear()
    read_binary_asset.cache_clear()
