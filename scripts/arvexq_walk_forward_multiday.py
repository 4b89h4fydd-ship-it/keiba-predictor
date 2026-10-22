#!/usr/bin/env python3
"""Read-only multi-day walk-forward of existing ARVEXQ learned forecast and diagnostic
ablation. No new prediction route, no production changes or database persistence.
Validation: Oct16-19; held-out check: Oct20-21. Train strictly on earlier dates.
"""
import copy,hashlib,json
from collections import Counter,defaultdict
from datetime import date,timedelta
from scripts.arvexq_provisional_real_pilot import day
from scripts.arvexq_current_prediction_audit import scrub_for_replay,finish_order
from arvexq.prediction.learned_scenarios import fit_model,FEATURES,race_family
from arvexq.prediction.new_forecast import build_forecast

START=date(2026,10,15)
END=date(2026,10,21)
HOLDOUT=date(2026,10,20)
CANDIDATES={
 "without_recent_form":("recent_finish_mean",),
 "without_track_fit":("same_track_finish",),
 "without_form_track":("recent_finish_mean","same_track_finish"),
 "without_finish_spread":("finish_spread",)
}

def ablate(model,fields):
    m=copy.deepcopy(model)
    n=len(FEATURES)
    for f in fields:
        i=FEATURES.index(f)
        m["weights"][i]=m["weights"][i+n]=0.0
    m["researchAblatedFeatures"]=list(fields)
    payload={k:v for k,v in m.items() if k!="modelHash"}
    m["modelHash"]=hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False,separators=(",",":")).encode()).hexdigest()
    return m

def compare_day(rows,circuit,models,ds):
    metrics={name:Counter() for name in models}
    differences=Counter()
    for r in rows:
        if r.get("circuit")!=circuit or (r.get("result") or {}).get("status")!="確定":
            continue
        if race_family(r)!="flat":continue
        result=finish_order(r)
        if not result or result[0] is None:continue
        # Scrub outcome, history later than target, and stored picks before predicting.
        input_race=scrub_for_replay(r,ds)
        picks={}
        for name,model in models.items():
            try:
                pred=build_forecast(input_race,model)
                if pred.get("predictionStatus")!="candidate-analysis":
                    metrics[name]["no_mark"]+=1
                    continue
                marked=[int(h["horseNumber"]) for h in pred.get("horses",[]) if (h.get("integratedEvaluation") or {}).get("mark")=="◎"]
                if len(marked)!=1:
                    metrics[name]["no_mark"]+=1
                    continue
                pick=marked[0]
                picks[name]=pick
                metrics[name]["scored"]+=1
                metrics[name]["hit"]+=int(pick==result[0])
                metrics[name]["top3"]+=int(pick in result[:3])
            except (TypeError,ValueError,KeyError,OverflowError) as exc:
                metrics[name]["errors"]+=1
                metrics[name]["error_"+type(exc).__name__]+=1
        if "original" in picks:
            for name,pick in picks.items():
                if name=="original":continue
                if pick!=picks["original"]:
                    differences[name+"_changed"]+=1
                    differences[name+"_fixed"]+=int(pick==result[0])
                    differences[name+"_regressed"]+=int(picks["original"]==result[0])
    return metrics,dict(differences)

dates=[(START+timedelta(days=i)).isoformat() for i in range((END-START).days+1)]
all_days={}
failures={}
for ds in dates:
    try:all_days[ds]=day(ds)
    except Exception as exc:
        failures[ds]=type(exc).__name__
        print("WALK_FORWARD_DAY_FETCH_FAILURE",json.dumps({"day":ds,"error":type(exc).__name__}),flush=True)
if failures:raise SystemExit("Incomplete date coverage; fail closed: "+json.dumps(failures))
for circuit in ("中央","地方"):
    hist=[]
    reports=[]
    for ds in dates:
        target=all_days[ds]
        historical=[r for r in hist if r.get("circuit")==circuit]
        try:
            model=fit_model(historical,circuit=circuit)
        except ValueError as e:
            print("WALK_FORWARD_NO_MODEL",json.dumps({"circuit":circuit,"day":ds,"earlier_races":len(historical),"reason":str(e)},ensure_ascii=False),flush=True)
            hist.extend(target)
            continue
        models={"original":model,**{name:ablate(model,fields) for name,fields in CANDIDATES.items()}}
        metrics,changes=compare_day(target,circuit,models,ds)
        if metrics["original"]["scored"]:
            result={"day":ds,"phase":"holdout" if ds>=HOLDOUT.isoformat() else "validation",
                    "training":model["training"]["races"],"metrics":{k:dict(v) for k,v in metrics.items()},"changes":changes}
            reports.append(result)
            print("WALK_FORWARD_DAY",json.dumps({"circuit":circuit,**result},ensure_ascii=False),flush=True)
        hist.extend(target)
    validation=[r for r in reports if r["phase"]=="validation"]
    holdout=[r for r in reports if r["phase"]=="holdout"]
    if not validation or not holdout:
        print("WALK_FORWARD_INSUFFICIENT",json.dumps({"circuit":circuit,"validation_days":len(validation),"holdout_days":len(holdout)},ensure_ascii=False),flush=True)
        continue
    def total(rows,name):
        out=Counter()
        for row in rows:out.update(row["metrics"][name])
        return {"scored":out["scored"],"hit":out["hit"],"top3":out["top3"],"no_mark":out["no_mark"],"errors":out["errors"]}
    baseline=total(validation,"original")
    better=[name for name in CANDIDATES if total(validation,name)["scored"]==baseline["scored"] and total(validation,name)["hit"]>baseline["hit"] and total(validation,name)["errors"]==baseline["errors"]]
    selected=sorted(better,key=lambda n:(-total(validation,n)["hit"],n))[0] if better else None
    comparison={name:{"validation":total(validation,name),"holdout":total(holdout,name)} for name in ["original",*CANDIDATES]}
    confirmed=bool(selected and comparison[selected]["holdout"]["hit"]>comparison["original"]["holdout"]["hit"]
              and comparison[selected]["holdout"]["scored"]==comparison["original"]["holdout"]["scored"]
              and comparison[selected]["holdout"]["errors"]==comparison["original"]["holdout"]["errors"])
    print("WALK_FORWARD_FINAL",json.dumps({"circuit":circuit,"validation_dates":[r["day"] for r in validation],
     "holdout_dates":[r["day"] for r in holdout],"candidates":comparison,"selected_on_validation":selected,
     "improved_on_holdout":confirmed,"decision":"research_candidate_only" if confirmed else "reject_keep_existing",
     "caveat":"Postrace snapshots may contain mutated input fields; not verified original pre-off forecasts."},ensure_ascii=False),flush=True)
