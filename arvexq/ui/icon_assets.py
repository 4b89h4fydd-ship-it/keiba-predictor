"""Runtime and PWA icon asset loader. The original PNG bytes are preserved."""
from __future__ import annotations
import base64
from functools import lru_cache
from pathlib import Path

_STATIC = Path(__file__).resolve().parent / "static"
_FILES = {"192": "arvexq-icon-source-192.png",
          "512": "arvexq-icon-source-512.png"}

@lru_cache(maxsize=1)
def load_icons() -> dict[str, str]:
    """Recreate the historical base64 API without embedding images in app.py."""
    return {size: base64.b64encode((_STATIC / filename).read_bytes()).decode("ascii")
            for size, filename in _FILES.items()}
