"""Chronological whole-race fusion replay using EXISTING D1 race bundles.

A replay is NOT represented as an original preoff capture. Current-race result,
payout, odds and postrace metadata are removed before candidate calculations.
Only previously trained models and dated prior starts can affect an outcome.
Official result and payout are joined AFTER predictions have been calculated.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from datetime import datetime
from hashlib import sha256
from zoneinfo import ZoneInfo
import json

from arvexq.prediction.fusion_method_models import (
    fit_observed_methods, predict_observed_methods,
)
from arvexq.prediction.fusion_ai_models import fit_two_ais, predict_logistic, predict_bayes
from arvexq.prediction.empirical_fusion import VERSION, _arms, _probs
from arvexq.prediction.fusion_settlement import _finishers, _official_single_win_payout

JST = ZoneInfo("Asia/Tokyo")
HORSE_PREOFF_KEYS = frozenset((
    "horseNumber", "name", "age", "sex", "frameNumber", "jockey",
    "trainer", "carriedWeight", "weight", "recentRaces", "allPastRuns",
    "careerArchive", "careerTransport", "pastRaces", "history", "runs",
    "visionResearchHistory",
))
RACE_PREOFF_KEYS = frozenset((
    "id", "date", "circuit", "track", "surface", "distance", "distanceM",
    "scheduledStartTime", "startTime", "fieldSize", "raceNumber",
    "title", "class", "grade", "condition", "going", "analysisMode",
))


def _preoff_card(snapshot):
    if not isinstance(snapshot, dict):
        raise ValueError("historical race detail required")
    if not isinstance(snapshot.get("horses"), list):
        raise ValueError("historical starter list required")
    clean = {k:deepcopy(v) for k,v in snapshot.items() if k in RACE_PREOFF_KEYS}
    clean["horses"] = [
        {k:deepcopy(v) for k,v in horse.items() if k in HORSE_PREOFF_KEYS}
        for horse in snapshot["horses"] if isinstance(horse, dict)
    ]
    return clean


def _eligible(snapshot, circuit):
    if not isinstance(snapshot, dict) or snapshot.get("circuit") != circuit:
        return False
    if "帯広" in str(snapshot.get("track") or "") or snapshot.get("surface") in ("障害","ばんえい"):
        return False
    if (snapshot.get("result") or {}).get("status") != "確定":
        return False
    if not isinstance(snapshot.get("date"), str) or not snapshot.get("id"):
        return False
    try:
        _finishers(snapshot)
        _official_single_win_payout(snapshot)
    except (ValueError,TypeError,KeyError):
        return False
    return True


def _replay_opinions(card, models):
    """Return simulated as-of predictions; the clock is NOT actual capture."""
    day = card["date"]
    start = str(card.get("scheduledStartTime") or card.get("startTime") or "")
    if len(start) < 5:
        raise ValueError("scheduled off missing in historical preoff racecard")
    off = datetime.fromisoformat(day+"T"+start[:5]+":00").replace(tzinfo=JST)
    cutoff = datetime.fromisoformat(day+"T00:00:00").replace(tzinfo=JST)
    if cutoff >= off:
        raise ValueError("cannot establish strictly-before-off replay cutoff")
    now, scheduled = cutoff.isoformat(), off.isoformat()
    arms = predict_observed_methods(
        card, models["methods"], captured_at=now, scheduled_off_at=scheduled)
    arms["ai:learned"] = predict_logistic(
        card, models["ai"]["ai:learned"], captured_at=now, scheduled_off_at=scheduled)
    arms["ai:bayes"] = predict_bayes(
        card, models["ai"]["ai:bayes"], captured_at=now, scheduled_off_at=scheduled)
    _arms(arms)
    for name, row in arms.items():
        row["captureInterpretation"] = "SIMULATED-ASOF-CUTOFF-NOT-ORIGINAL-PREOFF"
        row["replayCutoffAt"] = row.pop("capturedAt")
        row["sourceKind"] += "-chronological-replay"
        if not row.get("evidenceId"):
            raise ValueError("method evidence absent")
    return arms


def fit_replay_calibration(records, *, circuit, target_date, min_races=30):
    """Measure real returns on blinded earlier-date simulated predictions.

    Important: no receipt is represented as originally frozen. This is a
    historical time-split evaluation with explicit provenance and audit of
    each model's training date before the validation event.
    """
    if circuit not in ("中央","地方") or not isinstance(records,list):
        raise ValueError("circuit and evaluation records required")
    if len(records)<min_races:
        raise ValueError("fewer than 30 eligible blind out-of-time races")
    seen,versions,totals={},None,defaultdict(lambda:{"races":0,"wins":0,"top3":0,"stake":0.,"return":0.})
    for row in records:
        rid, day, methods = row["raceId"], row["raceDate"], row["arms"]
        if row.get("circuit")!=circuit or day>=target_date or rid in seen:
            raise ValueError("mixed circuit, future labels or duplicate replay")
        if row.get("replayMode")!="chronological-heldout-no-actual-preoff-receipt":
            raise ValueError("unaudited chronological replay")
        seen[rid]=day
        names=_arms(methods)
        this_versions={k:v["modelVersion"] for k,v in methods.items()}
        if versions is None:
            versions=this_versions
        elif versions!=this_versions:
            raise ValueError("models changed within validation cohort")
        roster=row["roster"]
        if len(roster)<5 or len(set(roster))!=len(roster):
            raise ValueError("invalid heldout starter roster")
        actual=row["actualWinner"]
        if actual not in roster or row["officialWinPayoutPer100Yen"]<0:
            raise ValueError("unverified official settlement")
        top3=set(row["actualTop3"])
        for method,candidate in methods.items():
            if candidate.get("captureInterpretation")!="SIMULATED-ASOF-CUTOFF-NOT-ORIGINAL-PREOFF":
                raise ValueError("replay cannot impersonate a frozen original")
            if candidate.get("modelTrainingThrough","") >= day:
                raise ValueError("winner result leaked into earlier model training")
            scores=_probs(candidate["win"],roster)
            best=min(scores,key=lambda no:(-scores[no],no))
            stat=totals[method]
            stat["races"]+=1
            stat["wins"]+=int(best==actual)
            stat["top3"]+=int(best in top3)
            stat["stake"]+=100.
            stat["return"]+=row["officialWinPayoutPer100Yen"] if best==actual else 0.
    if len(seen)<min_races:
        raise ValueError("insufficient independent blind replay races")
    raw={name:(v["wins"]/v["races"])*(v["return"]/v["stake"])
         for name,v in totals.items()}
    mass=sum(raw.values())
    if mass<=0:
        raise ValueError("no method won with positive recorded official returns")
    metrics={name:{
        "races":v["races"],"winHits":v["wins"],
        "winHitRate":v["wins"]/v["races"],
        "honmeiTop3Hits":v["top3"],"honmeiTop3Rate":v["top3"]/v["races"],
        "stakeYen":v["stake"],"returnYen":v["return"],
        "roi":v["return"]/v["stake"],
    } for name,v in sorted(totals.items())}
    return {
        "version":VERSION,"circuit":circuit,
        "targetDate":target_date,"trainedThrough":max(seen.values()),
        "nRaces":len(seen),"evaluatedRaceIds":sorted(seen),
        "weights":{k:raw[k]/mass for k in sorted(raw)},
        "methodVersions":dict(sorted(versions.items())),
        "metrics":metrics,"formula":"independent holdout win accuracy x official ¥100 win return multiple",
        "calibrationMethod":"chronological-replay-not-original-frozen",
        "weightsIndependentOfTargetOutcome":True,
        "notActualPreoffReceipts":True,
    }


def train_and_validate(details, *, circuit, target_date, min_races=30,
                       max_validation=50, max_training=90):
    """One fixed earlier train/holdout split, exact JRA/NAR separation.

    Later holdout labels NEVER enter either AI/expert fit. All five predictions
    are computed from the preoff-only card before the official payout is read.
    """
    if circuit not in ("中央","地方"):
        raise ValueError("separate JRA and NAR models required")
    eligible=sorted((d for d in details if _eligible(d,circuit) and d["date"]<target_date),
                    key=lambda d:(d["date"],d["id"]))
    ids=[r["id"] for r in eligible]
    if len(ids)!=len(set(ids)):
        raise ValueError("duplicate historical race IDs")
    days=sorted({row["date"] for row in eligible})
    # Prefer the most recent entire heldout day while keeping >=30
    # independent training races. The earliest split forced JRA onto just
    # one incomplete weekend day, despite later pre-target history.
    pivot=next((day for day in reversed(days[1:]) if
               sum(d["date"]<day for d in eligible)>=min_races and
               sum(d["date"]>=day for d in eligible)>=min_races),None)
    if pivot is None:
        raise ValueError("insufficient separate earlier training and later evaluation days")
    train=[d for d in eligible if d["date"]<pivot][-max_training:]
    valid=[d for d in eligible if d["date"]>=pivot][:max_validation]
    if len(train)<min_races or len(valid)<min_races:
        raise ValueError("chronological holdout too small")
    train_safe=[]
    for row in train:
        clean=_preoff_card(row)
        clean["result"]={"status":"確定","finishers":deepcopy(row["result"]["finishers"])}
        train_safe.append(clean)
    models={
        "methods":fit_observed_methods(
            train_safe,circuit=circuit,target_date=pivot,min_races=min_races),
        "ai":fit_two_ais(
            train_safe,circuit=circuit,target_date=pivot,min_races=min_races),
    }
    replay,excluded=[],{}
    for actual in valid:
        card=_preoff_card(actual)
        try:
            opinions=_replay_opinions(card,models)
            order=_finishers(actual)
            official_no,payout=_official_single_win_payout(actual)
            if order[0]!=official_no:
                raise ValueError("official win payout conflicts with winning horse")
            roster=[h["horseNumber"] for h in card["horses"]]
            if set(order)-set(roster):
                raise ValueError("unmatched official finish field")
            training_through={
                name:model["trainingThrough"] for name,model in models["methods"].items()
            }
            training_through["ai:learned"]=models["ai"]["ai:learned"]["training"]["lastDate"]
            training_through["ai:bayes"]=models["ai"]["ai:bayes"]["trainingThrough"]
            for name,opinion in opinions.items():
                opinion["modelTrainingThrough"]=training_through[name]
            replay.append({
                "raceId":card["id"],"raceDate":card["date"],"circuit":circuit,
                "replayMode":"chronological-heldout-no-actual-preoff-receipt",
                "roster":roster,"arms":opinions,
                "actualWinner":order[0],"actualTop3":order[:3],
                "officialWinPayoutPer100Yen":payout,
            })
        except (ValueError,KeyError,TypeError,OverflowError,ZeroDivisionError) as exc:
            excluded[str(card.get("id"))]=str(exc)
    calibrated=fit_replay_calibration(
        replay,circuit=circuit,target_date=target_date,min_races=min_races)
    model_hash=sha256(json.dumps(
        {k:{name:model["modelVersion"] if k=="methods" else
             model.get("modelHash") for name,model in group.items()}
         for k,group in models.items()},sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    return {
        "models":models,"calibration":calibrated,
        "audit":{
            "version":"arvexq-five-method-heldout-v1",
            "circuit":circuit,"targetDate":target_date,
            "trainingRaces":len(train_safe),"trainingThrough":max(d["date"] for d in train),
            "validationRaces":len(replay),"validationThrough":max(d["date"] for d in valid),
            "validationExcluded":excluded,
            "modelEvidenceHash":model_hash,
            "notActualOriginalPreoffCapture":True,
            "noTargetRaceResultUsed":True,
        },
    }
