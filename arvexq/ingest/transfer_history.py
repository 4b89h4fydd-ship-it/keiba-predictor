"""Observed horse career rates separated from prediction, marks, and betting.

Never use outcomes dated on or after the target race date, nor merge
incomparable JRA/NAR denominators.
"""
from arvexq.ingest.circuit_transfer import race_circuit as _run_circuit, _observed_day

def _history_rates(horse, race):
    cutoff = _observed_day(race.get("date") or race.get("raceDate"))
    target = _run_circuit(race)
    source = horse.get("allPastRuns") or horse.get("recentRaces") or []
    # Invalid or future-dated records cannot be compared in a pre-race evaluation.
    runs = []
    if cutoff is not None:
        for run in source:
            if not isinstance(run, dict):
                continue
            day = _observed_day(run.get("date") or run.get("raceDate"))
            if day is None or day >= cutoff:
                continue
            try:
                finish = float(run.get("finish"))
            except (TypeError, ValueError):
                continue
            if not (finish.is_integer() and 1 <= finish <= 100):
                continue
            # Copy, never rewrite source evidence, and normalize only validated ranks.
            runs.append({**run, "finish": int(finish)})
    runs.sort(key=lambda x: _observed_day(x.get("date") or x.get("raceDate")), reverse=True)
    # An unknown target must never silently become a local/NAR race.
    same = [r for r in runs if _run_circuit(r) == target] if target else []
    other = [r for r in runs if _run_circuit(r) not in (target, None)] if target else []
    unknown = [r for r in runs if _run_circuit(r) is None]
    def level(run):
        try:
            v = float(run.get("opponentLevel"))
            return v if 0 <= v <= 1 else None
        except (ValueError, TypeError): return None
    tl = level(race)
    def field_size(run):
        try:
            n = int(run.get("fieldSize") or 0)
            return n if n > 1 and int(run["finish"]) <= n else None
        except (TypeError, ValueError, OverflowError):
            return None
    comparable = [r for r in other if tl is not None and level(r) is not None
                  and field_size(r) is not None]
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
