"""Central-only data-backed retrospective comparison; never impute margins."""
import argparse,base64,copy,gzip,hashlib,json,sys
from pathlib import Path
from collections import Counter
from arvexq.prediction.past_performance import observed_runs
from arvexq.prediction.factor_model import rank_factor_model, collect_horse_raw_metrics
from arvexq.ingest.full_career import merge_career
from arvexq.core.runner_status import is_inactive_runner
from arvexq.research.mineta_field_proxy import score_race
from arvexq.research.margin_abcde_candidate import score as margin_score
from scripts.arvexq_current_prediction_audit import api_json,finish_order

def evaluate(bundle=None, target_date=None):
    outcomes={}
    supplemental={d['id']:d for d in (bundle or {}).get('details') or [] if d.get('circuit') in ('JRA','中央')}
    if bundle:
        outcomes={(d['date'],d['id']):finish_order(d) for d in supplemental.values()}
    else:
        for day in ("2026-10-07","2026-10-08","2026-10-09","2026-10-10","2026-10-11","2026-10-12","2026-10-13"):
            for d in api_json("https://kraiz-api.4b89h4fydd.workers.dev/api/day?date="+day+"&details=1").get("details") or []:
                order=finish_order(d)
                if len(order)>=3:outcomes[(d.get("date"),d.get("id"))]=order
    counts=Counter();races=[]
    for p in sorted(Path("arvexq/ui/static/saved-snapshots").glob("*.json")):
        envelope=json.loads(p.read_text())
        if "gzipBase64" not in envelope:continue
        raw=gzip.decompress(base64.b64decode(envelope["gzipBase64"],validate=True))
        if hashlib.sha256(raw).hexdigest()!=envelope["sha256"]:raise ValueError("archive checksum")
        d=json.loads(raw)
        if d.get("circuit") not in ("JRA","中央"):continue
        if target_date and d.get('date')!=target_date:continue
        counts["JRA_snapshots"]+=1
        order=outcomes.get((d.get("date"),d.get("id")))
        if not order:continue
        counts["JRA_with_result"]+=1
        d=copy.deepcopy(d)
        # Only prior-start measurements are supplemented. Preserve the original
        # target racecard and model context; scores never receive target results.
        fresh={int(h['horseNumber']):h for h in supplemental.get(d['id'],{}).get('horses') or []}
        for h in d.get('horses') or []:
            other=fresh.get(int(h['horseNumber']),{})
            if other.get('name')!=h.get('name'):continue
            original=observed_runs(h,d,limit=5)
            dates={r['date'] for r in original}
            incoming=[r for r in observed_runs(other,d,limit=5) if r['date'] in dates]
            merged=merge_career(original,incoming,d['date'])
            h['recentRaces']=merged;h['allPastRuns']=merged;h.pop('careerArchive',None)
        d.pop('result',None)
        hs=[h for h in d.get("horses") or [] if not is_inactive_runner(h)]
        positions=score_race(hs,d)
        margins={int(h["horseNumber"]):margin_score(h,d) for h in hs}
        counts["horses"]+=len(hs)
        counts["horses_with_margin"]+=sum(v is not None for v in margins.values())
        counts["horses_with_mineta"]+=len(positions)
        nos={int(h["horseNumber"]) for h in hs}
        counts['horses_with_current_inputs']+=sum(all(collect_horse_raw_metrics(h,d).get(k) is not None for k in ('trueRun','pure','sectional')) for h in hs)
        complete_margins=all(observed_runs(h,d,limit=5) and all(
            r.get('timeBehindWinner') is not None or r.get('marginSeconds') is not None
            for r in observed_runs(h,d,limit=5)) for h in hs)
        current_complete=all(all(collect_horse_raw_metrics(h,d).get(k) is not None
             for k in ('trueRun','pure','sectional')) for h in hs)
        if not complete_margins or not current_complete or len(nos)!=len(hs) or order[0] not in nos or set(positions)!=nos or any(x is None for x in margins.values()):
            counts["missing_same_race_inputs"]+=1
            continue
        curr={int(r["horse"]["horseNumber"]):r["score"] for r in rank_factor_model(hs,d)}
        if set(curr)!=nos:continue
        methods={"mineta":positions,
          "mineta_current_60_40":{n:.6*positions[n]+.4*curr[n] for n in nos},
          "mineta_margin_60_40":{n:.6*positions[n]+.4*margins[n]["score"] for n in nos},
          "mineta_current_margin_60_20_20":{n:.6*positions[n]+.2*curr[n]+.2*margins[n]["score"] for n in nos}}
        projections={}
        for name,values in methods.items():
            order_by_score=sorted(nos,key=lambda n:(-values[n],n))
            projections[name]={"first":order_by_score[0],"winnerRank":order_by_score.index(order[0])+1}
        races.append({"id":d["id"],"date":d["date"],"winner":order[0],"predictions":projections})
    summary={k:{"races":len(races),"winnerHits":sum(r["predictions"][k]["winnerRank"]==1 for r in races),"winnerTop3Hits":sum(r["predictions"][k]["winnerRank"]<=3 for r in races),
        "winnerRate":sum(r["predictions"][k]["winnerRank"]==1 for r in races)/len(races) if races else None,
        "winnerTop3Rate":sum(r["predictions"][k]["winnerRank"]<=3 for r in races)/len(races) if races else None} for k in ("mineta","mineta_current_60_40","mineta_margin_60_40","mineta_current_margin_60_20_20")}
    return {"status":"tested" if len(races)>=5 else "insufficient-verified-central-inputs","centralOnly":True,"evaluationType":"retrospective-only",
       "minetaDefinition":"existing observable positioning proxy; not Mineta's proprietary full method",
       "eligibility":"Every active horse: positions, all sampled prior margins, and all current score axes observed","sourceCounts":dict(counts),"methods":summary,"raceRows":races,"productionChanged":False,"historicalSnapshotNotBlind":True}

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument('output');p.add_argument('--bundle');p.add_argument('--date');a=p.parse_args()
    data=evaluate(json.loads(Path(a.bundle).read_text()) if a.bundle else None,a.date)
    Path(a.output).write_text(json.dumps(data,ensure_ascii=False,indent=2))
    print("JRA_MINETA_COMPARISON="+json.dumps({k:v for k,v in data.items() if k!='raceRows'},ensure_ascii=False))
