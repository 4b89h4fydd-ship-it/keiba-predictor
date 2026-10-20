"""Owned definitions, installed in the original app context by components.runtime.

The migration bridge preserves existing global state, decorators and monkeypatch
contracts. These definitions are not independently initialized modules yet.
"""

def _prepared_ttl(detail: dict) -> int:
    # Today's cards can change (odds/body weight/result). Old races are effectively static.
    return int(os.getenv("PREPARED_TODAY_TTL_SEC","45")) if str(detail.get("date") or "")==_today_iso() else int(os.getenv("PREPARED_ARCHIVE_TTL_SEC","21600"))

def _prepared_get_fresh(race_id: str) -> dict | None:
    detail,updated=PREPARED_STORE.get(race_id)
    if not detail or not updated or not _racedb_snapshot_usable(detail):return None
    # Retired prediction fields must not trigger an analysis refresh.
    detail=_restore_saved_odds(detail)
    try:
        detail["dataCoreHealth"]=_data_core_health(detail);detail["dataCoreVersion"]=ARVEXQ_DATA_CORE_VERSION
    except Exception:pass
    return detail
