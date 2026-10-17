#!/usr/bin/env python3
"""Compare research scores on the SAME final races; retrospective, not pre-off proof."""
import json
import math
import base64
import gzip
import hashlib
from collections import defaultdict
from datetime import date,timedelta
from pathlib import Path
from scripts.arvexq_current_prediction_audit import api_json,finish_order,scrub_for_replay
from arvexq.research.sequential_challengers import candidates
from arvexq.research.margin_abcde_candidate import score as margin_abcde_score, num
from arvexq.prediction.past_performance import observed_runs
from arvexq.research.mineta_position_proxy import position_proxy
from arvexq.research.mineta_field_proxy import score_race as mineta_field_scores

def summarize_five(five):
    chosen=five[:5]
    labels={
        "mineta_field_proxy":"Mineta observable-position proxy only",
        "mineta_current_60_40":"Mineta 60% + current 40%",
        "mineta_margin_60_40":"Mineta 60% + margin-focused 40%",
        "mineta_current_margin_60_20_20":"Mineta 60% + current 20% + margin-focused 20%",
    }
    comparison={}
    for name,label in labels.items():
        comparable=[]
        for race in chosen:
            forecast=(race.get("mixedForecasts") or {}).get(name) or {}
            if isinstance(forecast.get("winnerRank"),int) and forecast.get("winnerRank")>0:
                comparable.append((race,forecast))
        hits=sum(x["winnerRank"]==1 for _,x in comparable)
        top3=sum(x["winnerRank"]<=3 for _,x in comparable)
        comparison[name]={
            "label":label,"eligible":len(comparable),"fiveRaceCount":len(chosen),
            "top1Hits":hits,"winnerTop3Hits":top3,
            "top1Rate":round(hits/len(comparable),6) if comparable else None,
            "winnerTop3Rate":round(top3/len(comparable),6) if comparable else None,
            "completeSameFive":len(comparable)==5 and len(chosen)==5,
            "byCircuit":{c:{
                "eligible":sum(r["circuit"]==c for r,_ in comparable),
                "top1Hits":sum(r["circuit"]==c and x["winnerRank"]==1 for r,x in comparable)
            } for c in ("中央","地方")},
        }
    shared=[r for r in chosen if all(
        (r.get("mixedForecasts") or {}).get(name,{}).get("winnerRank") is not None
        for name in labels)]
    same_five={
        "races":len(chosen),"fullyComparableRaces":len(shared),
        "allThreeCombinationsComparableOnFive":len(chosen)==5 and len(shared)==5,
        "labels":labels,
        "missingMethodCount":{k:5-v["eligible"] for k,v in comparison.items()},
        "warning":"No evidence-free margins or positions are invented; unavailable means untested, not a loss.",
    }
    return comparison, same_five


def evaluate():
    raise RuntimeError("Retired fixed-weight comparison; use arvexq_learned_scenario_evaluation.py")

if __name__=="__main__":
    from sys import argv
    out=evaluate()
    Path(argv[1]).write_text(json.dumps(out,ensure_ascii=False,indent=2)+chr(10))
    print("RESULT="+json.dumps(out,ensure_ascii=False))
