"""Convert immutable feature snapshots plus independent capture receipts.

No result, mark, ticket or pre-existing prediction score enters feature creation.
The receipt is REQUIRED and must originate from an actual pre-off acquisition log.
This adapter checks consistency; it cannot authenticate external clock evidence.
"""
from __future__ import annotations

from hashlib import sha256
import json

from .race_softmax_research import _allowed_feature, _validate_race


def _hash_snapshot(snapshot):
    data = {k: v for k, v in snapshot.items() if k != "featureHash"}
    raw = json.dumps(data, ensure_ascii=False, sort_keys=True,
                     separators=(",", ":"), default=str).encode("utf-8")
    return sha256(raw).hexdigest()


def from_frozen_snapshot(snapshot, receipt, finishers=None):
    """Create a complete research race with labels joined only after freezing.

    receipt must identify a separately retained, genuinely earlier acquisition.
    A post-race snapshot with retroactively entered times is NOT proof of pre-off
    availability. Callers must validate the receipt at the storage boundary.
    """
    if not isinstance(snapshot, dict) or not isinstance(receipt, dict):
        raise ValueError("frozen snapshot and independent receipt required")
    digest = snapshot.get("featureHash")
    if not isinstance(digest, str) or digest != _hash_snapshot(snapshot):
        raise ValueError("frozen feature hash mismatch")
    if (receipt.get("raceId") != snapshot.get("raceId")
            or receipt.get("featureHash") != digest
            or receipt.get("attestedPreOff") is not True
            or receipt.get("source") != "preoff-acquisition-log"):
        raise ValueError("separately verified pre-off acquisition receipt required")
    declared = receipt.get("activeHorseNumbers")
    if not isinstance(declared, list) or not declared:
        raise ValueError("official active-runner roster required")
    rows = snapshot.get("rows") or []
    indexed = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("invalid frozen runner row")
        no = row.get("horseNumber")
        if type(no) is not int or no <= 0 or no in indexed:
            raise ValueError("duplicate frozen runner identity")
        indexed[no] = row
    if any(no not in indexed for no in declared):
        raise ValueError("official declared runner absent from frozen snapshot")
    results = None
    if finishers is not None:
        if not isinstance(finishers, list):
            raise ValueError("finishers must be separate labelled result rows")
        results = {}
        for row in finishers:
            if not isinstance(row, dict):
                raise ValueError("invalid finisher")
            no, rank = row.get("horseNumber"), row.get("finish")
            if type(no) is not int or type(rank) is not int or no in results:
                raise ValueError("invalid finisher identity or finish")
            results[no] = rank
        if set(results) != set(declared):
            raise ValueError("result field does not match original active field")
    track = str(snapshot.get("track") or "")
    surface = str(snapshot.get("surface") or "")
    family = ("banei" if "帯広" in track else "jumps" if "障" in surface else "flat")
    horses = []
    for no in declared:
        features = indexed[no].get("features")
        if not isinstance(features, dict):
            raise ValueError("frozen features missing")
        horse = {"horseNumber": no,
                 "features": {k: v for k, v in features.items() if _allowed_feature(k)}}
        if results is not None:
            horse["finish"] = results[no]
        horses.append(horse)
    race = {"raceId": snapshot.get("raceId"), "date": snapshot.get("date"),
            "circuit": snapshot.get("circuit"), "family": family,
            "snapshotHash": digest,
            "capturedAtEpoch": receipt.get("capturedAtEpoch"),
            "postAtEpoch": receipt.get("postAtEpoch"),
            "declaredHorseNumbers": list(declared), "horses": horses}
    return _validate_race(race, labelled=results is not None)
