"""Versioned, circuit-owned prospective cohort and local forecast envelopes."""
from datetime import date, datetime, timezone, timedelta
from hashlib import sha256
from pathlib import Path
from copy import deepcopy
import re
from arvexq.research.stage63.forward import canonical, digest, write_once
from .circuits import CONFIGS, circuit
from .pipeline import predict

ARMS=("baseline","recent5","recent5_shrunk")
JST=timezone(timedelta(hours=9))
RACE=("id","date","circuit","track","surface","analysisMode","startTime",
      "scheduledStartTime","distance","raceNumber","courseGeometry","fieldSize")
HORSE=("horseNumber","status","scratched","withdrawn","cancelled")
RUN=("date","_raceDate","track","surface","analysisMode","raceId","raceNumber",
     "distance","fieldSize","finish","cornerPositions","passing",
     "marginSeconds","timeBehindWinner","opponentLevel","earlyTiming",
     "class","className")
EARLY_TIMING=("sourceKind","sourceRef","gateReactionSeconds","first200mSeconds")


def code_hash():
    roots=(Path(__file__).parent,Path(__file__).parent.parent/"stage63")
    return digest({root.name+"/"+p.name:sha256(p.read_bytes()).hexdigest()
                   for root in roots for p in sorted(root.glob("*.py"))})


def make_plan(owner, development_ids):
    if owner not in CONFIGS:
        raise ValueError("unknown circuit")
    return {"schema":"arvexq-stage64-plan-1","circuit":owner,
            "startDate":"2026-10-21","endDate":"2026-11-19",
            "developmentThrough":"2026-10-20",
            "developmentIds":sorted(set(development_ids)),
            "codeSha256":code_hash(),"config":deepcopy(CONFIGS[owner]),"arms":ARMS,
            "cohortPolicy":"all races in supplied saved input batch; freeze failures abort whole batch",
            "unscoredPolicy":"retain all frozen races; no outcome-based deletion",
            "minimumScoredRaces":100,"minimumRaceDates":10,
            "ticketLimit":10,"simulationUnitYen":100,
            "retuningAllowed":False,"productionPromotionAllowed":False}


def check_plan(plan):
    if canonical(plan)!=canonical(make_plan(plan["circuit"],plan["developmentIds"])):
        raise ValueError("plan or code changed")


def post_at(race):
    clock=race.get("startTime")
    if not isinstance(clock,str) or not re.fullmatch(r"\d{2}:\d{2}",clock):
        raise ValueError("explicit HH:MM scheduled post required")
    return datetime.fromisoformat(race["date"]+"T"+clock+":00").replace(tzinfo=JST)


def _frozen_prior_rows(rows, cutoff):
    """Only dated, pre-off historical facts; never transport target/future finishes."""
    if not isinstance(rows, list):
        return []
    frozen = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        day = row.get("_raceDate") or row.get("date")
        try:
            if (not isinstance(day, str) or date.fromisoformat(day).isoformat() != day
                    or day >= cutoff):
                continue
        except ValueError:
            continue
        fact = {k: deepcopy(row[k]) for k in RUN if k in row and k != "earlyTiming"}
        timing = row.get("earlyTiming")
        if isinstance(timing, dict):
            fact["earlyTiming"] = {
                k: deepcopy(timing[k]) for k in EARLY_TIMING if k in timing
            }
        frozen.append(fact)
    return frozen


def clean_input(race):
    if any(race.get(k) for k in ("result","results","payouts")):
        raise ValueError("target outcome present")
    clean={k:deepcopy(race[k]) for k in RACE if k in race}
    clean["horses"]=[]
    is_nar = race.get("circuit") in ("nar", "地方")
    for horse in race["horses"]:
        h={k:deepcopy(horse[k]) for k in HORSE if k in horse}
        h["recentRaces"]=_frozen_prior_rows(horse.get("recentRaces"),race["date"])
        # NAR has an independently registered full-career policy. Preserve
        # only eligible dated facts, not the opaque archive or result labels.
        if is_nar and isinstance(horse.get("allPastRuns"),list):
            h["allPastRuns"]=_frozen_prior_rows(horse["allPastRuns"],race["date"])
        transport=horse.get("careerTransport")
        if (is_nar and isinstance(transport,dict)
                and type(transport.get("observedRuns")) is int
                and transport["observedRuns"] >= 0):
            h["careerTransport"]={"observedRuns":transport["observedRuns"]}
        clean["horses"].append(h)
    return clean


def snapshot(race, plan):
    check_plan(plan)
    owner=circuit(race)
    if owner!=plan["circuit"] or race["id"] in plan["developmentIds"] or not plan["startDate"]<=race["date"]<=plan["endDate"]:
        raise ValueError("race outside prospective circuit/cohort")
    off=post_at(race)
    now=datetime.now(timezone.utc)
    if now>=off:
        raise ValueError("race already started")
    source=clean_input(race)
    predictions={arm:predict(source,expected_circuit=owner,ability_method=arm) for arm in ARMS}
    data={"raceId":race["id"],"circuit":owner,"capturedAt":now.isoformat(),
          "scheduledOffAt":off.isoformat(),"planSha256":digest(plan),
          "inputSha256":digest(source),"input":source,"predictions":predictions}
    return {"snapshot":data,"snapshotSha256":digest(data)}


def verify_local(receipt, plan):
    check_plan(plan)
    data=receipt["snapshot"]
    race=data["input"]
    if digest(data)!=receipt["snapshotSha256"] or digest(race)!=data["inputSha256"] or digest(plan)!=data["planSha256"]:
        raise ValueError("receipt/input/plan checksum mismatch")
    if circuit(race)!=plan["circuit"] or data["circuit"]!=plan["circuit"] or data["raceId"]!=race["id"]:
        raise ValueError("receipt identity mismatch")
    if race["id"] in plan["developmentIds"] or not plan["startDate"]<=race["date"]<=plan["endDate"]:
        raise ValueError("development overlap or invalid cohort date")
    off=post_at(race)
    stamp=datetime.fromisoformat(data["capturedAt"])
    if stamp.tzinfo is None or stamp>=off or datetime.fromisoformat(data["scheduledOffAt"])!=off:
        raise ValueError("invalid local preoff chronology")
    if canonical(clean_input(race))!=canonical(race):
        raise ValueError("non-feature fields in receipt")
    expected={arm:predict(race,expected_circuit=plan["circuit"],ability_method=arm) for arm in ARMS}
    if canonical(expected)!=canonical(data["predictions"]):
        raise ValueError("prediction recomputation mismatch")
    return {"localIntegrityVerified":True,"independentlyVerifiedPreoff":False}


def freeze_batch(path, races, plan):
    if not races or len({r["id"] for r in races})!=len(races):
        raise ValueError("empty/duplicate cohort")
    # Calculate the complete batch before the sole write. No partially frozen cohort.
    receipts=[snapshot(race,plan) for race in races]
    batch={"schema":"arvexq-stage64-batch-1","planSha256":digest(plan),
           "cohort":sorted(r["id"] for r in races),"receipts":receipts}
    write_once(path,batch)
    return batch
