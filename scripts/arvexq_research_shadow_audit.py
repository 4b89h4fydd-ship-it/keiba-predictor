#!/usr/bin/env python3
"""Read-only D1 research shadow audit; no model promotion, no retrospective replay."""
from __future__ import annotations
import argparse
import json
import os
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime,timedelta
from pathlib import Path
from arvexq.prediction.prerace_archive import JST
from arvexq.prediction.research_evaluation import evaluate_race,summarize
from scripts.arvexq_fetch_d1_bundle import get_json,detail_from_response


def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--api-base",default=os.getenv("CLOUDFLARE_API_BASE","https://kraiz-api.4b89h4fydd.workers.dev"))
    ap.add_argument("--days",type=int,default=14)
    ap.add_argument("--end-date",default="")
    ap.add_argument("--out",default="research-shadow-evaluation.json")
    args=ap.parse_args()
    end=datetime.strptime(args.end_date,"%Y-%m-%d").date() if args.end_date else datetime.now(JST).date()-timedelta(days=1)
    base=args.api_base.rstrip("/")
    days=[(end-timedelta(days=i)).isoformat() for i in range(min(max(args.days,1),90))]
    discovered={}
    for day in days:
        payload=get_json(base+"/api/day?date="+urllib.parse.quote(day)+"&details=0",
                         timeout=30,retries=4)
        for race in payload.get("races") or []:
            if isinstance(race,dict) and race.get("id"):
                discovered[str(race["id"])]=day
    reports=[];missing=0;errored=[]
    def fetch(rid):
        data=get_json(base+"/api/race/"+urllib.parse.quote(rid,safe=""),timeout=30,retries=4)
        detail=detail_from_response(data,rid)
        return evaluate_race(detail) if isinstance(detail,dict) else None
    if discovered:
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures={pool.submit(fetch,rid):rid for rid in discovered}
            for future in as_completed(futures):
                try:
                    result=future.result()
                    if result:reports.append(result)
                    else:missing+=1
                except Exception as exc:
                    errored.append({"raceId":futures[future],"error":str(exc)[:240]})
    report=summarize(reports)
    report["racesDiscovered"]=len(discovered)
    report["racesWithoutQualifyingResearchArchive"]=missing
    report["readErrors"]=errored
    report["coverageRate"]=round(len(reports)/len(discovered),4) if discovered else None
    Path(args.out).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print("RESEARCH_SHADOW_EVALUATION",json.dumps({
        k:report[k] for k in ("racesDiscovered","inputRaceCount","coverageRate",
                             "shadowWinnerHitRate","shadowBrierWin",
                             "shadowBrierTop3","readiness","promotionEligible")
    },ensure_ascii=False))
    # Fail on missing source availability so an empty dataset cannot masquerade
    # as a valid performance result. Sparse historical shadows are expected.
    return 2 if not discovered or errored else 0


if __name__=="__main__":
    raise SystemExit(main())
