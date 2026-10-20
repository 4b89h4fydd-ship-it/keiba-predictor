"""Owned definitions, installed in the original app context by components.runtime.

The migration bridge preserves existing global state, decorators and monkeypatch
contracts. These definitions are not independently initialized modules yet.
"""

def _compact_display_snapshot(detail: dict) -> dict:
    """Serve facts and fresh pre-off provisional marks, never obsolete archives."""
    if not isinstance(detail,dict):return detail
    from arvexq.forecast.publication import public_race
    out=public_race(detail)
    detail=out
    active_marks={}
    if out.get("predictionStatus")=="provisional":
        active_marks={
            str(m.get("horseNumber")):m for m in (out.get("predictionMarks") or [])
            if isinstance(m,dict) and m.get("mark") in {"◎","○","▲","△","☆"}
        }
    for key in ("aiEvaluation", "factorRanking", "honmeiDecision", "preRacePrediction",
                "predictionAudit", "frozenPredictionAudit", "winnerLearningProfile",
                "betRecommendations", "recommendedBets", "tickets", "buyList", "bets",
                "markMethod", "markEngineVersion", "predictionModelVersion"):
        out.pop(key, None)
    horses=[]
    for h in detail.get("horses",[]) or []:
        if not isinstance(h,dict):continue
        z=_sanitize_horse_measurements(h)
        runs=list(z.get("allPastRuns") or z.get("recentRaces") or [])
        z["recentRaces"]=runs[:5]
        z.pop("allPastRuns",None)
        z.pop("evaluationSources",None)
        for key in ("integratedEvaluation", "mark", "honmeiRole", "modelProbabilities",
                    "recommendedBets", "tickets", "bets"):
            z.pop(key,None)
        live=active_marks.get(str(z.get("horseNumber")))
        if live:
            z["mark"]=live["mark"]
            z["markProvisional"]=True
        horses.append(z)
    out["horses"]=horses
    pm=dict(out.get("preparedMeta") or {})
    pm["displayCompact"]=True
    out["preparedMeta"]=pm
    try:
        out["dataCoreHealth"]=_data_core_health(out);out["dataCoreVersion"]=ARVEXQ_DATA_CORE_VERSION
    except Exception:pass
    return out
