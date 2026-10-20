"""Observed horse career rates separated from prediction, marks, and betting.

Never use outcomes dated on or after the target race date, nor merge
incomparable JRA/NAR denominators.
"""
from arvexq.components.item_056.circuit_transfer import race_circuit as _run_circuit

def _history_rates(horse, race):
    cutoff = str(race.get("date") or "")
    target = "JRA" if str(race.get("circuit") or "") in ("中央", "JRA") else "NAR"
    source = horse.get("allPastRuns") or horse.get("recentRaces") or []
    runs = [r for r in source if isinstance(r, dict) and
            r.get("finish") is not None and str(r.get("date") or "") and
            (not cutoff or str(r.get("date")) < cutoff)]
    runs.sort(key=lambda x: str(x.get("date")), reverse=True)
    same = [r for r in runs if _run_circuit(r) == target]
    other = [r for r in runs if _run_circuit(r) not in (target, None)]
    unknown = [r for r in runs if _run_circuit(r) is None]
    def level(run):
        try:
            v = float(run.get("opponentLevel"))
            return v if 0 <= v <= 1 else None
        except (ValueError, TypeError): return None
    tl = level(race)
    comparable = [r for r in other if tl is not None and level(r) is not None
                  and int(r.get("fieldSize") or 0) > 1]
    quality = [((int(r["fieldSize"])-int(r["finish"]))/(int(r["fieldSize"])-1))*
               (0.5 + 0.5 * level(r)) for r in comparable]
    signal = ((sum(quality)/len(quality)-0.5) * len(quality)/(len(quality)+8)) if quality else 0.0
    n=len(same)
    wins=sum(int(r["finish"])==1 for r in same)
    top2=sum(int(r["finish"])<=2 for r in same)
    top3=sum(int(r["finish"])<=3 for r in same)
    shrink=n/(n+8) if n else 0.0
    return {
        "starts":n,"recordedStarts":len(runs),"sameCircuitStarts":n,
        "otherCircuitStarts":len(other),"unknownCircuitStarts":len(unknown),
        "latestRecordedCircuit":_run_circuit(runs[0]) if runs else None,
        "targetCircuit":target,"transferEvidence":bool(other),
        "transferClassEvidenceStarts":len(quality),"targetOpponentLevel":tl,
        "transferClassSignal":signal,
        "transferClassStatus":"observed-opponent-proxy-uncalibrated" if quality else "unknown-no-comparable-opponent-evidence",
        "winRate":wins/n if n else None,"top2Rate":top2/n if n else None,
        "top3Rate":top3/n if n else None,
        "winEvidence":shrink*(wins/n-0.12) if n else 0.0,
        "top2Evidence":shrink*(top2/n-0.25) if n else 0.0,
        "top3Evidence":shrink*(top3/n-0.38) if n else 0.0,
        "comparability":"same-circuit-only; cross-circuit-opponent-proxy-unverified"
    }
