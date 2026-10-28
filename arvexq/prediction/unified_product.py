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


def verified(race):
    """Revalidate immutable receipt and its hash, not only claimed IDs."""
    candidate = (race or {}).get("unifiedForecast")
    if not _core_valid(race, candidate):
        return None
    canonical = {k: v for k, v in candidate.items() if k != "receiptSha256"}
    digest = sha256(json.dumps(canonical, ensure_ascii=False, sort_keys=True,
                               separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    return candidate if candidate.get("receiptSha256") == digest else None


