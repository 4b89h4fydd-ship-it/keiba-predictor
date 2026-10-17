"""Audit pre-off evidence coverage; research-only and no model mutation."""
from collections import Counter
from arvexq.prediction.past_performance import observed_runs


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
            raw = {
                'trueRun': True if runs else None,
                'pure': True if any(r.get('opponentLevel') is not None for r in runs) else None,
                'sectional': True if any(r.get('last3fRank') is not None for r in runs) else None,
            }
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
                count["sectionalMissingWithObservedFinish"]+=1
                c["sectionalMissingWithObservedFinish"]+=1
    def summarize(c):
        out = dict(c)
        horses = c["horses"]
        out["noObservedRuns"] = c["withoutFiveRunEvidence"]
        out["fiveRunComplete"] = horses - c["fewerThanFiveRuns"]
        out["fiveRunCoverageRate"] = (out["fiveRunComplete"] / horses if horses else None)
        out["missingAnyRunRate"] = (c["withoutFiveRunEvidence"] / horses if horses else None)
        return out
    return {"overall":summarize(count),
            "byCircuit":{k:summarize(v) for k,v in sorted(by_circuit.items())},
            "disclaimer":"Coverage diagnosis, not prediction quality or observed future accuracy"}
