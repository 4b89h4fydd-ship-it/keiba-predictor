"""Lossless, versioned transfer archive for older career starts.

Keep the recent five raw for the mobile UI. Older observed runs are stored as
a compressed recoverable sidecar in the same D1 race JSON, never discarded.
No network calls or inferred races are used.
"""
from __future__ import annotations
import base64
import copy
import gzip
import hashlib
import json
from typing import Any
from arvexq.ingest.full_career import merge_career

SCHEME = "arvexq-career-gzip-json-v1"
MAX_UNCOMPRESSED = 15_000_000

# Small numeric/identity observations stay queryable on mobile; complete original
# observations remain losslessly preserved in careerArchive.
BROWSER_FIELDS = frozenset({
    "date","raceDate","raceId","raceNumber","raceNo","title","raceName",
    "track","venue","surface","trackType","distance","distanceM",
    "condition","going","weather","fieldSize","runners","finish",
    "finishPosition","rank","margin","marginSeconds","beatenLength",
    "timeSeconds","time","last3f","last3fRank","last600Rank",
    "cornerPositions","passing","speedIndex","horseFirst3FSeconds",
    "jockey","carriedWeight","weight","class","className","opponentLevel",
    "bodyWeight","frameNumber","horseNumber",
})


def _compact_run(run: dict[str, Any]) -> dict[str, Any]:
    return {k: copy.deepcopy(v) for k, v in run.items() if k in BROWSER_FIELDS}



def _serialized(rows: list[dict[str, Any]]) -> bytes:
    return json.dumps(rows, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), default=str).encode("utf-8")


def pack_horse(horse: dict[str, Any], race_date: str) -> dict[str, Any]:
    out = recover_horse(horse, race_date) if horse.get("careerArchive") else copy.deepcopy(horse)
    rows = merge_career(out.get("allPastRuns"), out.get("recentRaces"), race_date)
    if not rows:
        return out
    recent, older = rows[:5], rows[5:]
    out["recentRaces"] = recent
    out["allPastRuns"] = recent + [_compact_run(run) for run in older]
    if older:
        raw = _serialized(older)
        if len(raw) > MAX_UNCOMPRESSED:
            raise ValueError("Career archive larger than permitted uncompressed budget")
        out["careerArchive"] = {
            "encoding": SCHEME,
            "priorRaceDate": race_date,
            "olderRunCount": len(older),
            "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "payload": base64.b64encode(gzip.compress(raw, compresslevel=8, mtime=0)).decode("ascii"),
        }
    elif not out.get("careerArchive"):
        out.pop("careerArchive", None)
    out["careerTransport"] = {
        "version": SCHEME, "observedRuns": len(rows),
        "visibleRawRuns": len(recent), "compactOlderRuns": len(older),
        "packedOlderRuns": len(older),
        "lossless": True, "complete": (out.get("_careerHistoryAudit") or {}).get("complete") is True,
    }
    return out


def recover_horse(horse: dict[str, Any], race_date: str) -> dict[str, Any]:
    out = copy.deepcopy(horse)
    archive = out.get("careerArchive")
    if not isinstance(archive, dict):
        return out
    if archive.get("encoding") != SCHEME or archive.get("priorRaceDate") != race_date:
        raise ValueError("Career archive schema or race-date mismatch")
    zipped = base64.b64decode(str(archive["payload"]), validate=True)
    # Streaming bounded decompression protects against decompression bombs.
    import zlib
    decoder = zlib.decompressobj(wbits=31)
    raw = decoder.decompress(zipped, MAX_UNCOMPRESSED + 1)
    if len(raw) > MAX_UNCOMPRESSED or decoder.unconsumed_tail or not decoder.eof:
        raise ValueError("Career archive exceeds safe decompression budget")
    raw += decoder.flush()
    if len(raw) != int(archive.get("bytes") or 0):
        raise ValueError("Career archive size mismatch")
    if hashlib.sha256(raw).hexdigest() != archive.get("sha256"):
        raise ValueError("Career archive digest mismatch")
    older = json.loads(raw.decode("utf-8"))
    if not isinstance(older, list) or len(older) != archive.get("olderRunCount"):
        raise ValueError("Career archive run count mismatch")
    full = merge_career(out.get("allPastRuns"), older, race_date)
    if len(full) < int((out.get("careerTransport") or {}).get("observedRuns") or 0):
        raise ValueError("Career archive recovery incomplete")
    out["allPastRuns"] = full
    out["recentRaces"] = full[:5]
    return out


def pack_detail(detail: dict[str, Any]) -> dict[str, Any]:
    date = str(detail.get("date") or "")
    out = copy.deepcopy(detail)
    out["horses"] = [pack_horse(h, date) if isinstance(h, dict) else h
                     for h in (detail.get("horses") or [])]
    out.setdefault("preparedMeta", {})["careerTransportVersion"] = SCHEME
    return out
