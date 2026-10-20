"""Owned definitions, installed in the original app context by components.runtime.

The migration bridge preserves existing global state, decorators and monkeypatch
contracts. These definitions are not independently initialized modules yet.
"""

def _data_core_snapshot(race_id:str)->dict|None:
    return _prepared_get_fresh(race_id) or _racedb_get_fast(race_id) or _fast_local_race_detail(race_id)

def _racedb_get_fast(race_id:str)->dict|None:
    try:detail,updated=RACEDB.get_race(race_id)
    except Exception:return None
    if not detail or not _racedb_snapshot_usable(detail):return None
    if (detail.get("preparedMeta") or {}).get("fastPartial"):return detail
    if os.getenv("ARVEXQ_COLLECT_ONLY","0")!="1":
        if (detail.get("aiEvaluation") or {}).get("version")!=AI_EVALUATION_VERSION:
            detail=_precompute_detail_metrics(_strip_excluded(detail))
        detail=_ensure_race_volatility(detail)
    detail=_restore_saved_odds(detail)
    return detail
