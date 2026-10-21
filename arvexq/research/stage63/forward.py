"""Fail-closed, write-once local protocol/forecast receipts.

Checksums and user-supplied timestamps cannot authenticate pre-off availability.
An external timestamp witness is still required; this module never certifies it.
"""
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path

from .experiment import ARMS, predict

RACE_KEYS = ("id","date","circuit","startTime","fieldSize")
HORSE_KEYS = ("horseNumber","scratched","withdrawn","cancelled","recentRaces")
RUN_KEYS = ("date","_raceDate","fieldSize","finish","cornerPositions","passing")


def canonical(value):
    return json.dumps(value,sort_keys=True,ensure_ascii=False,
                      separators=(",",":"),allow_nan=False).encode()


def digest(value):
    return sha256(canonical(value)).hexdigest()


def code_digest():
    return digest({p.name:sha256(p.read_bytes()).hexdigest()
                   for p in sorted(Path(__file__).parent.glob("*.py"))})


def protocol(development_ids):
    return {"schema":"arvexq-stage63-plan-1","circuit":"nar",
            "notBeforeDate":"2026-10-20","endDate":"2026-11-18",
            "developmentThrough":"2026-10-19",
            "developmentRaceIds":sorted(set(development_ids)),
            "arms":ARMS,"codeSha256":code_digest(),
            "ticketLimit":10,"evaluationUnitYen":100,
            "minimumRaces":100,"minimumDates":10,
            "metrics":["coverage","winnerTop1","winnerTop3","logloss",
                       "brier","trifectaHitRate","roi","top2ReturnShare"],
            "cohort":"all available NAR saved cards, no post-outcome selection",
            "missingPolicy":"retain unscored races in coverage and all-race hit denominator",
            "earlyStoppingOrRetuning":False,"productionPromotion":False}


def write_once(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    raw = canonical(payload)+b"\n"
    fd = os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,"wb") as f:
        f.write(raw);f.flush();os.fsync(f.fileno())


def freeze(path, race, plan):
    now = datetime.now(timezone.utc)
    if canonical(plan) != canonical(protocol(plan["developmentRaceIds"])):
        raise ValueError("protocol/code changed")
    if race.get("result") or race.get("results") or race.get("payouts"):
        raise ValueError("target outcome already present")
    if race["id"] in plan["developmentRaceIds"] or race["date"] <= plan["developmentThrough"] or not plan["notBeforeDate"] <= race["date"] <= plan["endDate"]:
        raise ValueError("development data cannot be held out")
    off = datetime.fromisoformat(race["date"]+"T"+race["startTime"]+":00+09:00")
    if now >= off:
        raise ValueError("post time has passed")
    # Narrow whitelist: no target results, odds, payouts or archived predictions.
    clean = {k:race[k] for k in RACE_KEYS if k in race}
    clean["horses"] = []
    for horse in race["horses"]:
        h = {k:horse[k] for k in HORSE_KEYS if k in horse and k != "recentRaces"}
        h["recentRaces"] = [{k:r[k] for k in RUN_KEYS if k in r}
                            for r in horse.get("recentRaces") or []]
        clean["horses"].append(h)
    predictions = {arm:predict(clean,arm) for arm in ARMS}
    snapshot = {"raceId":race["id"],"circuit":"nar",
                "capturedAt":now.isoformat(),"scheduledOffAt":off.isoformat(),
                "planSha256":digest(plan),"sourceSha256":digest(clean),
                "input":clean,"predictions":predictions}
    receipt = {"snapshot":snapshot,"snapshotSha256":digest(snapshot),
               "independentlyVerifiedPreoff":False,
               "provenance":"local-checksum-only"}
    write_once(path,receipt)
    return receipt


def verify(receipt, plan):
    snap = receipt["snapshot"]
    if digest(snap) != receipt["snapshotSha256"] or digest(snap["input"]) != snap["sourceSha256"]:
        raise ValueError("tampered input or receipt")
    if digest(plan) != snap["planSha256"] or canonical(plan)!=canonical(protocol(plan["developmentRaceIds"])):
        raise ValueError("plan/code mismatch")
    race = snap["input"]
    if snap["raceId"]!=race["id"] or snap["circuit"]!="nar":
        raise ValueError("identity mismatch")
    if race["date"]<=plan["developmentThrough"] or not plan["notBeforeDate"]<=race["date"]<=plan["endDate"] or race["id"] in plan["developmentRaceIds"]:
        raise ValueError("development overlap")
    off = datetime.fromisoformat(race["date"]+"T"+race["startTime"]+":00+09:00")
    captured = datetime.fromisoformat(snap["capturedAt"])
    if captured.tzinfo is None or captured >= off or datetime.fromisoformat(snap["scheduledOffAt"])!=off:
        raise ValueError("invalid preoff chronology")
    expected = {arm:predict(race,arm) for arm in ARMS}
    if canonical(expected)!=canonical(snap["predictions"]):
        raise ValueError("forecast/code mismatch")
    return {"localIntegrityVerified":True,"independentlyVerifiedPreoff":False,
            "independentEvaluationEligible":False,
            "blocker":"Authenticated external timestamp binding plan, input and forecasts is required."}
