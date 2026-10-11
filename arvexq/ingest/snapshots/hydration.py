"""snapshots/hydration: original PR #13 acquisition orchestration.

Storage, evaluation and provider callbacks are explicit keyword-only ports.
Worker behavior, source priority and immutable prediction handling are preserved.
"""
from arvexq.infra.snapshot_status import _merge_card_rows_preserve
from arvexq.ingest.history.run_merge import _merge_fast_history
from arvexq.ingest.local.state import _nar_sync_io_lock
from arvexq.prediction.pure_diagnostics import _diagnosis_history_quality
from arvexq.prediction.pure_diagnostics import _history_is_enough
from datetime import datetime
import json
import re
import time


def _hydrate_fast_card_now(race_id: str, deep_history: bool=False, *, CENTRAL_DB_PATH, CentralStore, NarSync, RACEDB, _fast_local_race_detail, _history_counts, _jra_fetch_environment, _jra_find_cname, _jra_parse_race, _merge_current_card_fields, _merge_result_fields, _nar_official_card_rows_fast, _nar_official_result_fast, _nar_result_should_be_available, _netkeiba_card_rows_fast, _netkeiba_past_rows_fast, _new_conn, _now_jst, _start_race_history_search, _store_fast_snapshot, _today_iso) -> None:
    if race_id.startswith("nar-"):
        m=re.match(r"^nar-(\d{4}-\d{2}-\d{2})-(.+)-(\d{2})$",race_id)
        if not m:return
        iso_date,track,race_no=m.group(1),m.group(2),int(m.group(3))
        sync=None
        try:
            target=datetime.strptime(iso_date,"%Y-%m-%d").date()
            sync=NarSync()
            with _nar_sync_io_lock:
                if iso_date==_today_iso():sync.sync_daily(force=False)
                else:sync.sync_month(target.year,target.month,force=False)
        except Exception as exc:
            print("fast NAR date hydrate failed",race_id,exc)
        finally:
            try:
                if sync:sync.store.conn.close()
            except Exception:pass
        q=_fast_local_race_detail(race_id)
        if q:
            # Finished/started races: RaceMarkTable is the fastest authoritative source and also
            # carries body weight. Before the race, use the official card from multiple layouts.
            official_result=None
            if _nar_result_should_be_available(q):
                try:official_result=_nar_official_result_fast(q)
                except Exception as exc:print("fast NAR official result failed",race_id,exc)
            if official_result:
                q["result"]=official_result
                if official_result.get("weather") not in (None,"","不明"):q["weather"]=official_result["weather"]
                if official_result.get("condition") not in (None,"","不明"):q["condition"]=official_result["condition"]
                q=_merge_result_fields(q,official_result)
                q["bodyWeightSource"]="NAR公式競走成績"
                q["bodyWeightUpdatedAt"]=_now_jst().strftime("%H:%M:%S")
            else:
                try:q=_merge_current_card_fields(q,_nar_official_card_rows_fast(q))
                except Exception as exc:print("fast NAR official body weight failed",race_id,exc)
            _store_fast_snapshot(q)
            if deep_history:
                names=[str(h.get("name") or "") for h in q.get("horses",[]) if h.get("name")]
                cov=_history_counts(names,iso_date)
                if names and not _history_is_enough(cov,0):
                    _start_race_history_search(race_id,iso_date,names,force=False)
        return

    m=re.match(r"^jra-(20\d{2}-\d{2}-\d{2})-([^\-]+)-(\d{2})$",race_id)
    if not m:return
    date,track,rno=m.group(1),m.group(2),int(m.group(3))
    base=None
    if CENTRAL_DB_PATH.exists():
        conn=_new_conn(CENTRAL_DB_PATH)
        try:
            row=conn.execute("SELECT payload FROM central_races WHERE id=?",(race_id,)).fetchone()
            if row:
                try:base=json.loads(row["payload"])
                except Exception:base=None
        finally:conn.close()
    if not base:
        base={"id":race_id,"circuit":"中央","date":date,"track":track,"raceNumber":rno,
              "title":f"{rno}R","distance":0,"surface":"","condition":"不明","weather":"不明",
              "horses":[],"source":"高速出走表"}

    rows=_netkeiba_card_rows_fast(base)
    if rows:
        base=_merge_card_rows_preserve(base,rows)
        base["id"]=race_id;base["circuit"]="中央"
        # Weather/going is a separate lightweight feed; do not let the fast
        # horse-card path leave the race at "不明".
        if date==_today_iso() and (base.get("weather") in (None,"","不明") or base.get("condition") in (None,"","不明")):
            try:
                env=_jra_fetch_environment(base)
                if env.get("weather") not in (None,"","不明"):base["weather"]=env["weather"]
                if env.get("condition") not in (None,"","不明"):base["condition"]=env["condition"]
                if env:base["environmentMeta"]={"source":env.get("source","JRA公式優先"),"updatedAtEpoch":env.get("updatedAtEpoch",int(time.time()))}
            except Exception as exc:print("fast JRA environment failed",race_id,exc)
        # One past page hydrates all starters; collector does this before the customer taps.
        if not _diagnosis_history_quality(base).get("ready"):
            base=_merge_fast_history(base,_netkeiba_past_rows_fast(base))
        try:
            st=CentralStore();st.upsert([base]);st.conn.close()
        except Exception as exc:print("fast card central save failed",exc)
        try:RACEDB.upsert_race(base)
        except Exception as exc:print("fast card racedb save failed",exc)
        q=_fast_local_race_detail(race_id)
        if q:_store_fast_snapshot(q)
        return

    # Official fallback only after the faster single-page route fails.
    try:
        cname=_jra_find_cname(date,track,rno)
        live=_jra_parse_race(cname,supplement_profiles=False) if cname else None
        if live:
            live["id"]=race_id
            st=CentralStore();st.upsert([live]);st.conn.close()
            q=_fast_local_race_detail(race_id)
            if q:_store_fast_snapshot(q)
    except Exception as exc:print("fast JRA card hydrate failed",race_id,exc)
