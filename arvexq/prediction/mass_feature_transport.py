"""Lossless, date-bound transfer archive for pre-off mass feature matrices.

The model snapshots are immutable feature evidence used for later backtests.
Store their exact JSON under a compressed envelope in D1 rather than repeating
2+ MB of verbose feature names in a race-detail row.
"""
from __future__ import annotations
import base64
import copy
import gzip
import hashlib
import json
import zlib
from typing import Any

SCHEME = "arvexq-mass-feature-gzip-json-v1"
MAX_UNCOMPRESSED_BYTES = 30_000_000


def _raw(snapshot: dict[str, Any]) -> bytes:
    return json.dumps(snapshot, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), default=str).encode("utf-8")


def _feature_hash(snapshot: dict[str, Any]) -> str:
    core = {k: v for k, v in snapshot.items() if k != "featureHash"}
    return hashlib.sha256(_raw(core)).hexdigest()


def archive_snapshot(snapshot: dict[str, Any], *, race_id: str, race_date: str, preserve_unverified_legacy: bool = False) -> dict[str, Any]:
    if not isinstance(snapshot, dict) or not snapshot.get("rows"):
        raise ValueError("mass feature snapshot has no rows")
    if str(snapshot.get("raceId") or "") != str(race_id or ""):
        raise ValueError("mass feature snapshot race mismatch")
    if str(snapshot.get("date") or "") != str(race_date or ""):
        raise ValueError("mass feature snapshot date mismatch")
    feature_hash = str(snapshot.get("featureHash") or "")
    if not feature_hash:
        raise ValueError("mass feature snapshot missing its original feature hash")
    origin_valid = feature_hash == _feature_hash(snapshot)
    if not origin_valid and not preserve_unverified_legacy:
        raise ValueError("mass feature snapshot origin hash mismatch")
    raw = _raw(snapshot)
    if len(raw) > MAX_UNCOMPRESSED_BYTES:
        raise ValueError("mass feature snapshot exceeds safe budget")
    return {
        "encoding": SCHEME,
        "raceId": race_id,
        "raceDate": race_date,
        "featureHash": feature_hash,
        "originHashVerified": origin_valid,
        "originStatus": "verified" if origin_valid else "legacy-unverified-not-for-training",
        "rawBytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "horseCount": int(snapshot.get("horseCount") or len(snapshot["rows"])),
        "payload": base64.b64encode(gzip.compress(raw, compresslevel=9, mtime=0)).decode("ascii"),
    }


def restore_snapshot(archive: dict[str, Any], *, race_id: str, race_date: str, allow_unverified_legacy: bool = False) -> dict[str, Any]:
    if not isinstance(archive, dict) or archive.get("encoding") != SCHEME:
        raise ValueError("unsupported mass feature archive")
    if str(archive.get("raceId") or "") != str(race_id or "") or str(archive.get("raceDate") or "") != str(race_date or ""):
        raise ValueError("mass feature archive race/date mismatch")
    try:
        zipped = base64.b64decode(str(archive.get("payload") or ""), validate=True)
        decoder = zlib.decompressobj(wbits=31)
        raw = decoder.decompress(zipped, MAX_UNCOMPRESSED_BYTES + 1)
        if not decoder.eof or decoder.unconsumed_tail or len(raw) > MAX_UNCOMPRESSED_BYTES:
            raise ValueError("mass feature archive decompression limit")
        raw += decoder.flush()
        if len(raw) != int(archive.get("rawBytes") or 0):
            raise ValueError("mass feature archive size mismatch")
        if hashlib.sha256(raw).hexdigest() != archive.get("sha256"):
            raise ValueError("mass feature archive digest mismatch")
        snapshot = json.loads(raw.decode("utf-8"))
    except (ValueError, TypeError, zlib.error, UnicodeError) as exc:
        raise ValueError("invalid mass feature archive") from exc
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get("rows"), list):
        raise ValueError("invalid mass feature rows")
    if str(snapshot.get("raceId") or "") != str(race_id) or str(snapshot.get("date") or "") != str(race_date):
        raise ValueError("mass feature archived snapshot identity mismatch")
    if snapshot.get("featureHash") != archive.get("featureHash"):
        raise ValueError("mass feature pre-race declared hash mismatch")
    if archive.get("originHashVerified") is False:
        if not allow_unverified_legacy:
            raise ValueError("legacy mass feature origin hash unverified; not eligible for training")
    elif _feature_hash(snapshot) != archive.get("featureHash"):
        raise ValueError("mass feature pre-race hash mismatch")
    if int(snapshot.get("horseCount") or 0) != int(archive.get("horseCount") or 0):
        raise ValueError("mass feature horse count mismatch")
    return snapshot


def pack_mass_detail(detail: dict[str, Any], *, preserve_unverified_legacy: bool = False) -> dict[str, Any]:
    out = copy.deepcopy(detail)
    snapshot = out.get("massFeatureSnapshot")
    if not isinstance(snapshot, dict):
        return out
    if not isinstance(out.get("preRacePrediction"), dict):
        raise ValueError("cannot archive mass feature matrix without pre-off forecast")
    archive = archive_snapshot(snapshot,
                               race_id=str(out.get("id") or out.get("raceId") or ""),
                               race_date=str(out.get("date") or ""),
                               preserve_unverified_legacy=preserve_unverified_legacy)
    if out.get("massFeatureHash") and out["massFeatureHash"] != archive["featureHash"]:
        raise ValueError("mass feature lock hash mismatch")
    out["massFeatureArchive"] = archive
    out["massFeatureHash"] = archive["featureHash"]
    out.pop("massFeatureSnapshot", None)
    return out


def recover_mass_detail(detail: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(detail)
    if isinstance(out.get("massFeatureSnapshot"), dict):
        return out
    archive = out.get("massFeatureArchive")
    if not isinstance(archive, dict):
        return out
    snapshot = restore_snapshot(archive,
                                race_id=str(out.get("id") or out.get("raceId") or ""),
                                race_date=str(out.get("date") or ""))
    if out.get("massFeatureHash") and out["massFeatureHash"] != snapshot["featureHash"]:
        raise ValueError("frozen mass feature hash differs from recovered archive")
    out["massFeatureSnapshot"] = snapshot
    return out
