"""Observed horse career rates separated from prediction, marks, and betting.

Never use outcomes dated on or after the target race date, nor merge
incomparable JRA/NAR denominators.
"""
_JRA_TRACKS = frozenset(("札幌","函館","福島","新潟","東京","中山","中京","京都","阪神","小倉"))
_NAR_TRACKS = frozenset(("門別","帯広","盛岡","水沢","浦和","船橋","大井","川崎","金沢","笠松","名古屋","園田","姫路","高知","佐賀"))

def _run_circuit(run):
    explicit = str(run.get("circuit") or run.get("organization") or "").strip().lower()
    if explicit in ("中央", "jra", "central"): return "JRA"
    if explicit in ("地方", "nar", "local"): return "NAR"
    track = str(run.get("track") or "").strip()
    if track in _JRA_TRACKS: return "JRA"
    if track in _NAR_TRACKS: return "NAR"
    return None

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
