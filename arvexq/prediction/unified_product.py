"""ARVEXQ unified, race-specific, single-source pre-off forecast product.

Every visible mark, race-pace observation and candidate ticket must originate
from the SAME previously trained, date-isolated model prediction. The video
channel stays unavailable until independently reviewed horse identities exist.
No after-off materialization and no Stage64 or subjective override.
"""
from __future__ import annotations

from datetime import datetime
from hashlib import sha256
import json
from math import isfinite

from arvexq.prediction.prerace_archive import JST, post_at

# The unified product's model identity is owned by the rewrite engine
# (the rewrite/ package, published by scripts/arvexq_rewrite_publish.py).
# The former learned-scenarios producer lane was removed; verification of
# stored receipts now pins this identity instead.
MODEL_VERSION = "arvexq-rewrite-v1-uncalibrated-prior"


def race_family(detail):
    if '帯広' in str(detail.get('track') or ''):
        return 'banei'
    if '障' in str(detail.get('surface') or '') or detail.get('analysisMode') == '障害' or '障害' in str(detail.get('title') or ''):
        return 'jumps'
    # Debut races must never inherit a model fitted on experienced flat runners.
    if detail.get('analysisMode') == '新馬' or '新馬' in str(detail.get('title') or '') or 'メイクデビュー' in str(detail.get('title') or ''):
        return 'debut'
    return 'flat'
from arvexq.core.runner_status import is_inactive_runner

VERSION = "arvexq-unified-live-v1"
SYMBOLS = ("◎", "○", "▲", "△", "☆", "注")
BET_KINDS = {"馬連", "ワイド", "馬単", "3連複", "3連単"}


def _timestamp(stamp):
    try:
        v = datetime.fromisoformat(str(stamp))
        return v.astimezone(JST) if v.tzinfo is not None else None
    except (ValueError, TypeError):
        return None


def _core_valid(race, source):
    if not isinstance(race, dict) or not isinstance(source, dict):
        return False
    if source.get("version") != VERSION or source.get("raceId") != race.get("id"):
        return False
    if source.get("raceDate") != race.get("date") or source.get("circuit") != race.get("circuit"):
        return False
    if source.get("modelVersion") != MODEL_VERSION or source.get("modelFamily") != race_family(race):
        return False
    if source.get("researchOnly") is not True or source.get("probabilitiesCalibrated") is not False:
        return False
    capture, off = _timestamp(source.get("capturedAt")), post_at(race)
    if not capture or not off or capture >= off or source.get("trainedThrough", "9999") >= race.get("date", ""):
        return False
    actual = {h.get("horseNumber"): h.get("name") for h in race.get("horses") or []
              if isinstance(h, dict) and not is_inactive_runner(h)}
    expected = {row.get("horseNumber"): row.get("name") for row in source.get("roster") or []
                if isinstance(row, dict)}
    if len(actual) < 3 or actual != expected:
        return False
    marks = source.get("marks")
    if not isinstance(marks, list) or not marks:
        return False
    seen, count = set(), 0
    for row in marks:
        if not isinstance(row, dict):
            return False
        no, symbol = row.get("horseNumber"), row.get("markSymbol")
        if type(no) is not int or no not in actual or no in seen or symbol not in SYMBOLS:
            return False
        seen.add(no)
        count += symbol == "◎"
    if count != 1:
        return False
    return True


# --- Receipt canonicalization -------------------------------------------------
# The receipt must bind the sealed CONTENT, never the last serializer's
# spelling of it. Payloads cross a JS boundary (the sync worker re-serializes
# with JSON.stringify / JSON.parse), which collapses integral floats to ints
# (2.0 -> 2) and -0.0 to 0. Python's type-sensitive json.dumps then produces
# a different canonical string for identical content, and every stored race
# failed verification (root cause of predictionStatus='disabled' on delivery,
# pinpointed 2026-10-31 on jra-2026-10-31-東京-11: only beta 2.0 -> 2 differed).
# Canonicalization is therefore by VALUE: integral floats normalize to ints
# before dumping, so the Python original and its JS round trip hash alike.
# Any change to an actual value, string, key or list still changes the digest.

# Keys the product generator (rewrite/output/api_shape.py) always emits as
# JSON floats. A JS round trip can only have turned their integral values
# into ints; restoring the float spelling at exactly these keys reproduces
# the legacy (pre-normalization) canonical string for receipts sealed
# before value canonicalization existed. The numeric value never changes.
_FLOAT_KEYS = frozenset((
    "beta", "winProbability", "top3Probability", "winProbabilityRange",
    "top3ProbabilityRange", "abilityScore", "pacePressure", "probability",
    "odds", "expectedValue",
))


def _value_canonical(value):
    if isinstance(value, float):
        if value == 0:
            return 0
        if value.is_integer() and abs(value) < 2 ** 53:
            return int(value)
        return value
    if isinstance(value, dict):
        return {k: _value_canonical(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_value_canonical(v) for v in value]
    return value


def _float_restored(value, key=None):
    if isinstance(value, dict):
        return {k: _float_restored(v, k) for k, v in value.items()}
    if isinstance(value, list):
        return [_float_restored(v, key) for v in value]
    if key in _FLOAT_KEYS and type(value) is int:
        return float(value)
    return value


def _receipt_digest(canonical):
    return sha256(json.dumps(canonical, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":"),
                             allow_nan=False).encode()).hexdigest()


def canonical_receipt(product):
    """Receipt digest for new seals: value-canonical, serializer-proof."""
    canonical = {k: v for k, v in product.items() if k != "receiptSha256"}
    return _receipt_digest(_value_canonical(canonical))


def verified(race):
    """Revalidate immutable receipt and its hash, not only claimed IDs."""
    candidate = (race or {}).get("unifiedForecast")
    if not _core_valid(race, candidate):
        return None
    canonical = {k: v for k, v in candidate.items() if k != "receiptSha256"}
    accepted = {
        # Current form: value-canonical (what canonical_receipt seals).
        _receipt_digest(_value_canonical(canonical)),
        # Legacy form, payload never re-serialized after sealing.
        _receipt_digest(canonical),
        # Legacy form, payload JS round-tripped (stored production rows).
        _receipt_digest(_float_restored(canonical)),
    }
    return candidate if candidate.get("receiptSha256") in accepted else None


