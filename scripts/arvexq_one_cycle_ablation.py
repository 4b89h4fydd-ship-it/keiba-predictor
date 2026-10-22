#!/usr/bin/env python3
"""One full research cycle: original marks -> score -> diagnose -> same model ablation -> untouched next day.
Uses existing fit_model and build_forecast, and only disables feature coefficients inside
a research copy of the SAME learned model. No production changes or race persistence.
"""
import copy,hashlib,json
from collections import Counter
from scripts.arvexq_provisional_real_pilot import day
from scripts.arvexq_current_prediction_audit import scrub_for_replay,finish_order
from arvexq.prediction.learned_scenarios import fit_model,FEATURES,race_family
from arvexq.prediction.new_forecast import build_forecast

def ablate(model,fields):
    model=copy.deepcopy(model)
    n=len(FEATURES)
    for name in fields:
        idx=FEATURES.index(name)
        model["weights"][idx]=0.
        model["weights"][idx+n]=0.
    model["researchAblatedFeatures"]=list(fields)
    # The original integrity contract covers all model artifact fields.
    original={k:v for k,v in model.items() if k!="modelHash"}
    model["modelHash"]=hashlib.sha256(json.dumps(original,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
    return model

def compare(races,models,stage):
    result={name:Counter() for name in models}
    transitions=Counter()
    cases=[]
    for d in races:
        if d.get("circuit")!="地方" or race_family(d)!="flat" or (d.get("result") or {}).get("status")!="確定":continue
        finish=finish_order(d)
        if not finish:continue
        clean=scrub_for_replay(d,d["date"])
        picks={}
        for name,model in models.items():
            try:
                pred=build_forecast(clean,model)
                if pred.get("predictionStatus")!="candidate-analysis":
                    result[name]["unscorable"]+=1
                    continue
                marks={int(h["horseNumber"]):(h.get("integratedEvaluation") or {}).get("mark") for h in pred["horses"] if h.get("horseNumber")}
                head=next((n for n,m in marks.items() if m=="◎"),None)
                if head is None:result[name]["unscorable"]+=1;continue
                picks[name]=head
                result[name]["scored"]+=1
                result[name]["wins"]+=int(head==finish[0])
                result[name]["top3"]+=int(head in finish[:3])
            except (ValueError,TypeError,KeyError,OverflowError):
                result[name]["error"]+=1
        if "original" in picks:
            for name,head in picks.items():
                if name=="original":continue
                if head!=picks["original"]:
                    transitions[name+"_changed"]+=1
                    if head==finish[0]:transitions[name+"_improved_to_winner"]+=1
                    elif picks["original"]==finish[0]:transitions[name+"_lost_winner"]+=1
                    if len(cases)<15:cases.append({"race":d["id"],"original":picks["original"],"modified":head,"winner":finish[0],"model":name})
    summary={"stage":stage,"date":races[0]["date"] if races else None,"versions":{name:{"scored":v["scored"],"wins":v["wins"],"top3":v["top3"],"unscorable":v["unscorable"],"errors":v["error"]} for name,v in result.items()},"changes":dict(transitions),"case_examples":cases}
    print("ONE_CYCLE_COMPARISON",json.dumps(summary,ensure_ascii=False),flush=True)
    return result

train=day("2026-10-15")
validation=day("2026-10-16")
untouched=day("2026-10-17")
groups={
  "without_recent_form":("recent_finish_mean",),
  "without_track_fit":("same_track_finish",),
  "without_form_and_track":("recent_finish_mean","same_track_finish"),
  "without_finish_spread":("finish_spread",)
}
model=fit_model(train,circuit="地方")
versions={"original":model,**{name:ablate(model,fields) for name,fields in groups.items()}}
first=compare(validation,versions,"validation")
base=first["original"]
eligible=[name for name in groups if first[name]["scored"]==base["scored"] and first[name]["wins"]>base["wins"]]
chosen=sorted(eligible,key=lambda k:(-first[k]["wins"],k))[0] if eligible else None
print("ONE_CYCLE_SELECTION",json.dumps({"selected":chosen,"baseline_hits":base["wins"],"validation_improvers":eligible},ensure_ascii=False),flush=True)
# Holdout assessed once, independently of model selection. Compare best eligible candidate;
# when none qualifies, show the strongest diagnostic candidate but do NOT propose promotion.
if chosen is None:
  chosen=max(groups,key=lambda k:first[k]["wins"])
final_train=fit_model(train+validation,circuit="地方")
hold=compare(untouched,{"original":final_train,chosen:ablate(final_train,groups[chosen])},"holdout_unseen_for_selection")
b=hold["original"];c=hold[chosen]
promote=chosen in eligible and b["scored"]==c["scored"] and c["wins"]>b["wins"] and not c["error"]
print("ONE_CYCLE_REPORT",json.dumps({"baseline_validation":dict(base),"candidate":chosen,
 "candidate_validation":dict(first[chosen]),"baseline_holdout":dict(b),"candidate_holdout":dict(c),
 "improvement_confirmed":promote,"action":"research_only_proposal" if promote else "reject_candidate_keep_existing",
 "warning":"Retrospective snapshots may contain later-mutated inputs; NOT certified contemporaneous predictions."},ensure_ascii=False),flush=True)
if not b["scored"]:raise SystemExit("No scorable held-out races")
