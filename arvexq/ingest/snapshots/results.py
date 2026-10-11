"""snapshots/results: original PR #13 acquisition orchestration.

Storage, evaluation and provider callbacks are explicit keyword-only ports.
Worker behavior, source priority and immutable prediction handling are preserved.
"""
from arvexq.infra.pure_snapshots import _merge_official_result
from arvexq.infra.snapshot_status import _result_has_podium


def _refresh_result_fast(race_id: str, *, _attach_nar_payouts, _compact_display_snapshot, _fast_local_race_detail, _jra_find_cname, _jra_parse_result, _jra_result_cname_from_card, _merge_result_fields, _nar_official_result_fast, _netkeiba_current_result, _prepared_get_fresh, _race_should_have_result, _racedb_get_fast, _store_fast_snapshot, central_race_detail, nar_race_detail) -> dict | None:
    """Refresh only authoritative result data; never rebuild history/diagnosis."""
    detail=_prepared_get_fresh(race_id) or _racedb_get_fast(race_id) or _fast_local_race_detail(race_id)
    if not detail:
        detail=nar_race_detail(race_id) if race_id.startswith("nar-") else central_race_detail(race_id)
    if not detail:return None

    official=None
    if race_id.startswith("nar-"):
        try:official=_nar_official_result_fast(detail)
        except Exception as exc:print("NAR fast result refresh failed",race_id,exc)
        if official:
            detail["result"]=official
            if official.get("weather") not in (None,"","不明"):detail["weather"]=official["weather"]
            if official.get("condition") not in (None,"","不明"):detail["condition"]=official["condition"]
            detail=_merge_result_fields(detail,official)
        elif _race_should_have_result(detail):
            try:
                nk=_netkeiba_current_result(detail)
                if nk:
                    detail["result"]=nk
                    detail=_merge_result_fields(detail,nk)
            except Exception as exc:print("NAR result fallback failed",race_id,exc)
        if _result_has_podium(detail):
            try:detail=_attach_nar_payouts(detail)
            except Exception as exc:print("NAR payout attach after result failed",race_id,exc)
    else:
        try:
            result_cname=str(detail.get("resultCname") or "")
            if not result_cname:
                cname=_jra_find_cname(str(detail.get("date") or ""),str(detail.get("track") or ""),int(detail.get("raceNumber") or 0))
                if cname:result_cname=_jra_result_cname_from_card(cname)
            parsed=_jra_parse_result(result_cname,detail) if result_cname else None
            if parsed:detail=_merge_official_result(detail,parsed)
        except Exception as exc:print("JRA fast result refresh failed",race_id,exc)
        if not _result_has_podium(detail) and _race_should_have_result(detail):
            try:
                nk=_netkeiba_current_result(detail)
                if nk:
                    detail["result"]=nk
                    detail=_merge_result_fields(detail,nk)
            except Exception as exc:print("JRA result fallback failed",race_id,exc)

    if _result_has_podium(detail):
        try:_store_fast_snapshot(detail)
        except Exception as exc:print("result snapshot save failed",race_id,exc)
    return _compact_display_snapshot(detail)
