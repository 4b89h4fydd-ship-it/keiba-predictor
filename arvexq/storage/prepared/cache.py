"""Stage 5 responsibilities with explicit runtime dependencies."""
from __future__ import annotations
from pathlib import Path
from fastapi import Query

def _prepared_ttl(detail: dict, *, _today_iso, os) -> int:
    return int(os.getenv('PREPARED_TODAY_TTL_SEC', '45')) if str(detail.get('date') or '') == _today_iso() else int(os.getenv('PREPARED_ARCHIVE_TTL_SEC', '21600'))

def _prepared_get_fresh(race_id: str, *, AI_EVALUATION_VERSION, ARVEXQ_DATA_CORE_VERSION, PREPARED_STORE, _data_core_health, _ensure_race_volatility, _precompute_detail_metrics, _racedb_snapshot_usable, _restore_saved_odds, _strip_excluded) -> dict | None:
    detail, updated = PREPARED_STORE.get(race_id)
    if not detail or not updated or (not _racedb_snapshot_usable(detail)):
        return None
    if (detail.get('preparedMeta') or {}).get('fastPartial'):
        return detail
    if (detail.get('aiEvaluation') or {}).get('version') != AI_EVALUATION_VERSION:
        detail = _precompute_detail_metrics(_strip_excluded(detail))
    detail = _ensure_race_volatility(detail)
    detail = _restore_saved_odds(detail)
    try:
        detail['dataCoreHealth'] = _data_core_health(detail)
        detail['dataCoreVersion'] = ARVEXQ_DATA_CORE_VERSION
    except Exception:
        pass
    return detail

def _racedb_get_fast(race_id: str, *, AI_EVALUATION_VERSION, RACEDB, _ensure_race_volatility, _precompute_detail_metrics, _racedb_snapshot_usable, _restore_saved_odds, _strip_excluded) -> dict | None:
    try:
        detail, updated = RACEDB.get_race(race_id)
    except Exception:
        return None
    if not detail or not _racedb_snapshot_usable(detail):
        return None
    if (detail.get('preparedMeta') or {}).get('fastPartial'):
        return detail
    if (detail.get('aiEvaluation') or {}).get('version') != AI_EVALUATION_VERSION:
        detail = _precompute_detail_metrics(_strip_excluded(detail))
    detail = _ensure_race_volatility(detail)
    detail = _restore_saved_odds(detail)
    return detail
