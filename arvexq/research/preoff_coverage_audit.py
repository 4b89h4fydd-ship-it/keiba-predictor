"""Audit pre-off evidence coverage; research-only and no model mutation."""
from collections import Counter
from arvexq.prediction.past_performance import observed_runs
from arvexq.prediction.factor_model import collect_horse_raw_metrics


def audit_races(races):
    count=Counter()
    by_circuit={}
    for race in races:
        circuit=str(race.get("circuit") or "unknown")
        c=by_circuit.setdefault(circuit,Counter())
        count["races"]+=1
        c["races"]+=1
        for horse in race.get("horses") or []:
            if not isinstance(horse,dict):
                continue
            count["horses"]+=1
            c["horses"]+=1
            runs=observed_runs(horse,race,limit=5)
            raw=collect_horse_raw_metrics(horse,race)
            if not runs:
                count["withoutFiveRunEvidence"]+=1
                c["withoutFiveRunEvidence"]+=1
            if len(runs)<5:
                count["fewerThanFiveRuns"]+=1
                c["fewerThanFiveRuns"]+=1
            for field in ("trueRun","pure","sectional"):
                if raw.get(field) is None:
                    count[field+"Missing"]+=1
                    c[field+"Missing"]+=1
            if raw.get("sectional") is None and raw.get("trueRun") is not None:
                count["neutralImputedSectional"]+=1
                c["neutralImputedSectional"]+=1
    return {"overall":dict(count),
            "byCircuit":{k:dict(v) for k,v in sorted(by_circuit.items())},
            "disclaimer":"Coverage diagnosis, not prediction quality or observed future accuracy"}
