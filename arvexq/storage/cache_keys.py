from __future__ import annotations

import hashlib
import json
from typing import Any


def stable_hash(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8", "ignore")).hexdigest()


def race_detail_key(race_id: str, version: str = "v1") -> str:
    return f"race-detail:{version}:{race_id}"


def horse_history_key(horse_key: str, version: str = "v1") -> str:
    return f"horse-history:{version}:{horse_key}"


def prediction_key(race_id: str, input_hash: str, version: str = "v1") -> str:
    return f"prediction:{version}:{race_id}:{input_hash}"
