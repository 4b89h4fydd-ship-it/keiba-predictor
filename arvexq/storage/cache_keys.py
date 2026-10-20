from __future__ import annotations

import hashlib
import json
from typing import Any


def stable_hash(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8", "ignore")).hexdigest()

from arvexq.components.item_143.race_detail_key import race_detail_key
from arvexq.components.item_144.horse_history_key import horse_history_key

def prediction_key(race_id: str, input_hash: str, version: str = "v1") -> str:
    return f"prediction:{version}:{race_id}:{input_hash}"
