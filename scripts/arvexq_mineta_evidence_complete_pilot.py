#!/usr/bin/env python3
"""Research ONLY. Find completed NAR races with independently measured
prior-race winner-time gaps for EVERY active entrant; never fill missing margins.
Existing immutable snapshots are read, never rewritten. Retrospective study.
"""
from __future__ import annotations
import argparse
import base64
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
import gzip
import hashlib
import json
import os
from pathlib import Path
import unicodedata

from arvexq.core.runner_status import is_inactive_runner
from arvexq.prediction.past_performance import observed_runs
from arvexq.research.mineta_field_proxy import score_race
from arvexq.research.margin_abcde_candidate import score as margin_score
from scripts.arvexq_current_prediction_audit import api_json, finish_order

VERSION = "arvexq-mineta-complete-observed-margin-extended-v2"
METHODS = ("mineta","mineta_current_60_40","mineta_margin_60_40","mineta_current_margin_60_20_20")
NAR_CODES = {"帯広ば","帯広","盛岡","水沢","浦和","船橋","大井","川崎",
             "金沢","笠松","名古屋","園田","姫路","高知","佐賀","門別"}


def norm(x):
    return "".join(unicodedata.normalize("NFKC",str(x or "")).split())


def candidate_run(run, cutoff):
    at = str(run.get("date") or run.get("raceDate") or "")
    track = str(run.get("track") or "")
    try:
        no = int(run.get("raceNumber") or run.get("raceNo") or 0)
    except (TypeError, ValueError):
        return None
    return (at,track,no) if at and at < cutoff and track in NAR_CODES and 1 <= no <= 12 else None


def gather_candidates(snapshot_dir, outcomes, max_candidates=20):
    skipped = Counter()
    eligible = []
    for file in sorted(Path(snapshot_dir).glob("*.json")):
        obj = json.loads(file.read_text(encoding="utf-8"))
        if "gzipBase64" not in obj: continue
        binary = gzip.decompress(base64.b64decode(obj["gzipBase64"],validate=True))
        if hashlib.sha256(binary).hexdigest() != obj["sha256"]:
            raise ValueError("immutable snapshot sha mismatch: "+file.name)
        d = json.loads(binary)
        if str(d.get("circuit") or "") not in ("地方","NAR"):
            skipped["jra-intentionally-separate"] += 1
            continue
        order = outcomes.get((str(d.get("date") or ""),str(d.get("id") or "")))
        if not order:
            skipped["unverified-result"] += 1
            continue
        horses = [h for h in d.get("horses") or []
                  if isinstance(h,dict) and not is_inactive_runner(h)]
        if len(horses)<5:
            skipped["too-few-active"] += 1
            continue
        nos = {int(h.get("horseNumber") or 0) for h in horses}
        if 0 in nos or len(nos)!=len(horses) or order[0] not in nos:
            skipped["bad-runner-identity"] += 1
            continue
        positions = score_race(horses,d)
        if set(positions)!=nos:
            skipped["mineta-incomplete-position"] += 1
            continue
        references={}
        for h in horses:
            no = int(h["horseNumber"])
            options=[]
            for run in observed_runs(h,d,limit=5):
                key = candidate_run(run,d["date"])
                if key and key not in [item[0] for item in options]:
                    options.append((key,run))
            references[no]=options
        if any(not items for items in references.values()):
            skipped["missing-prior-official-reference"] += 1
            continue
        # Prioritize dense corroborated histories; first five eligible is not assumed adequate.
        density = sum(min(3,len(items)) for items in references.values())
        eligible.append((density,d,order,horses,references))
    eligible.sort(key=lambda x:(-x[0],x[1]["date"],x[1]["id"]))
    return eligible[:max_candidates],dict(skipped),len(eligible)


def official_fetch(key):
    from app import _nar_official_result_fast
    at,track,race_no=key
    return _nar_official_result_fast({"date":at,"track":track,
        "raceNumber":race_no,"horses":[]})


def official_observation(key, name, source, finishers):
    if not isinstance(finishers,dict): return None,"official-unavailable"
    rows=finishers.get("finishers") or []
    match=[r for r in rows if norm(r.get("name"))==norm(name)]
    if len(match)!=1:
        return None,"unmatched-name"
    winner=[r for r in rows if int(r.get("finish") or 0)==1
            and float(r.get("timeSeconds") or 0)>0]
    if len(winner)!=1: return None,"winner-time-unavailable"
    own=float(match[0].get("timeSeconds") or 0)
    if not own: return None,"horse-time-unavailable"
    gap=round(own-float(winner[0]["timeSeconds"]),2)
    if not 0 <= gap <= 30: return None,"invalid-gap"
    result=dict(source)
    result["date"],result["track"],result["raceNumber"]=key
    result["timeBehindWinner"]=gap
    result["marginEvidenceSource"]="NAR official prior finishers, winner-relative seconds"
    if match[0].get("last3FSeconds") is not None:
        result["last3fSeconds"]=match[0]["last3FSeconds"]
    if match[0].get("marginText"):
        result["marginText"]=match[0]["marginText"]
    return result,"observed"


def summarize_comparisons(races):
    """Same race denominator; no threshold fitting or post-result score changes."""
    report={}
    for method in METHODS:
        n=len(races)
        hits=sum(r["predictions"][method]["winnerRank"]==1 for r in races)
        third=sum(r["predictions"][method]["winnerTop3"] for r in races)
        by_track={}
        for track in sorted({str(r["track"]) for r in races}):
            subset=[r for r in races if str(r["track"])==track]
            by_track[track]={
                "races":len(subset),
                "winnerHits":sum(r["predictions"][method]["winnerRank"]==1 for r in subset),
                "winnerTop3Hits":sum(r["predictions"][method]["winnerTop3"] for r in subset),
            }
        dates=sorted({r["date"] for r in races})
        cutoff=dates[len(dates)//2] if dates else None
        periods={}
        for label, subset in (
                ("earlier",[r for r in races if cutoff and r["date"]<cutoff]),
                ("later",[r for r in races if cutoff and r["date"]>=cutoff])):
            periods[label]={"races":len(subset),
                "winnerHits":sum(r["predictions"][method]["winnerRank"]==1 for r in subset),
                "winnerTop3Hits":sum(r["predictions"][method]["winnerTop3"] for r in subset)}
        report[method]={"races":n,"winnerHits":hits,"winnerTop3Hits":third,
            "winRate":hits/n if n else None,"winnerTop3Rate":third/n if n else None,
            "byTrack":by_track,"byPeriod":periods}
    paired={}
    primary=METHODS[1]
    for challenger in METHODS[2:]:
        gain=[r for r in races if r["predictions"][challenger]["winnerRank"]==1 and
              r["predictions"][primary]["winnerRank"]!=1]
        loss=[r for r in races if r["predictions"][primary]["winnerRank"]==1 and
              r["predictions"][challenger]["winnerRank"]!=1]
        paired[challenger]={"beatsCurrentBlend":len(gain),"losesToCurrentBlend":len(loss),
            "bothWin":sum(r["predictions"][primary]["winnerRank"]==1 and
                          r["predictions"][challenger]["winnerRank"]==1 for r in races),
            "winnerGainRaceIds":[r["raceId"] for r in gain],
            "winnerLossRaceIds":[r["raceId"] for r in loss]}
    return report,paired


def evaluate(max_candidates=80,max_requests=650,target_complete=25):
    raise RuntimeError("Retired fixed-weight comparison; use arvexq_learned_scenario_evaluation.py")


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--max-candidates",type=int,default=80)
    p.add_argument("--max-requests",type=int,default=650)
    p.add_argument("--target-complete",type=int,default=25)
    a=p.parse_args()
    report=evaluate(a.max_candidates,a.max_requests,a.target_complete)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("MINETA_COMPLETE_PILOT="+json.dumps({
        k:report[k] for k in ("status","sameRaceCount","targetComplete","candidateRaces","candidatesAttempted",
        "officialPriorResultRequests","sourceCoverage","methods","pairedVersusMinetaCurrent","distinctDates","raceRows")},ensure_ascii=False))


if __name__=="__main__":
    main()
