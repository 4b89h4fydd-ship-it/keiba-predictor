"""local/history: acquisition behavior preserved from PR #13 (95f2595).

Keyword-only ports are supplied by the application composition root.
This module never imports app or initializes storage/background workers.
"""
from arvexq.ingest.nar_career_coverage import nar_history_wave_slots
from arvexq.ingest.nar_career_coverage import official_history_complete
from arvexq.ingest.nar_career_coverage import pre_race_reported_starts
from arvexq.ingest.scheduling import _months_from_race_date
import json
import os
import threading


from arvexq.ingest.history.jobs import _race_history_jobs
from arvexq.ingest.history.jobs import _race_history_lock

def _history_counts(horse_names: list[str], cutoff: str, *, NarStore) -> dict:
    names = [x for x in dict.fromkeys(horse_names) if x]
    if not names:
        return {"totalHorses":0,"horsesWithHistory":0,"horsesWith4Plus":0,"horsesWith5Plus":0,"horsesWith6Plus":0,"totalRuns":0,"counts":{},"underFive":[]}
    store = NarStore()
    try:
        placeholders = ",".join("?" for _ in names)
        rows = store.conn.execute(
            f"SELECT name,COUNT(*) cnt FROM entries WHERE name IN ({placeholders}) AND date<? AND finish>0 GROUP BY name",
            (*names, cutoff),
        ).fetchall()
        cmap = {r["name"]: int(r["cnt"] or 0) for r in rows}
    finally:
        try: store.conn.close()
        except Exception: pass
    counts = {name: int(cmap.get(name, 0)) for name in names}
    vals = list(counts.values())
    return {
        "totalHorses": len(names),
        "horsesWithHistory": sum(1 for v in vals if v > 0),
        "horsesWith4Plus": sum(1 for v in vals if v >= 4),
        "horsesWith5Plus": sum(1 for v in vals if v >= 5),
        "horsesWith6Plus": sum(1 for v in vals if v >= 6),
        "totalRuns": sum(vals),
        "counts": counts,
        "underFive": [name for name, v in counts.items() if v < 5],
    }


def _start_race_history_search(race_id: str, iso_date: str, horse_names: list[str], force: bool=False, *, RACEDB, _build_fast_diagnosis_snapshot, _detail_cache, _detail_cache_lock, _history_counts, _supplement_sparse_nar_history, _sync_nar_month_wave) -> dict:
    max_months = max(6, min(36, int(os.getenv("NAR_ON_DEMAND_HISTORY_MONTHS", "36"))))
    # Race-date-bound start counts may already be recorded in the prepared
    # snapshot. They are the lower bound the official local DB must cover.
    # An unknown count is NOT evidence that five runs exhaust the lifetime.
    try:
        original = RACEDB.get_race(race_id)[0]
    except Exception:
        original = None
    required = pre_race_reported_starts(original, iso_date, horse_names)
    with _race_history_lock:
        existing = _race_history_jobs.get(race_id)
        if existing and not force:
            return dict(existing)
        cov = _history_counts(horse_names, iso_date)
        job = {"status":"running","monthsDone":0,"maxMonths":max_months,"coverage":cov,"error":"","source":"NAR公式月次レースデータ",
               "knownCareerStarts":len(required),"fullCareerVerified":official_history_complete(cov,required)}
        _race_history_jobs[race_id] = job

    def worker():
        errors = []
        months_done = 0
        months = list(_months_from_race_date(iso_date, max_months))
        wave = max(2, min(4, int(os.getenv("NAR_ON_DEMAND_WAVE_MONTHS", "3"))))
        try:
            for pos in range(0, len(months), wave):
                batch = months[pos:pos+wave]
                # Bound cross-race NAR ZIP downloads; the SQL import itself
                # also retains the existing single-writer lock.
                with nar_history_wave_slots:
                    _, errs = _sync_nar_month_wave(batch)
                errors.extend(errs)
                months_done += len(batch)
                cov_now = _history_counts(horse_names, iso_date)
                with _race_history_lock:
                    _race_history_jobs[race_id] = {"status":"running","monthsDone":months_done,"maxMonths":max_months,"coverage":cov_now,"error":" | ".join(errors[-3:]),"source":"NAR公式 高速並列履歴"}
                # Five runs are display data, not the complete career.
                # Stop only when every horse's official lifetime count for
                # this race date has been reached. Otherwise use the bounded
                # configured lookback, leaving coverage explicitly unverified.
                if official_history_complete(cov_now, required):
                    break
            cov_now = _history_counts(horse_names, iso_date)
            # v155: if official NAR history is still under five starts, search a second
            # career source. This is especially important for JRA/NAR transfers.
            supplemented=0
            under=list(cov_now.get("underFive") or [])
            if under:
                try:supplemented=_supplement_sparse_nar_history(race_id,under,iso_date)
                except Exception as exc:errors.append("netkeiba DB補完:"+str(exc))
            verified = official_history_complete(cov_now, required)
            status = "done" if verified else ("error" if errors and not (cov_now.get("horsesWithHistory",0)>0 or supplemented>0) else "partial")
            source="NAR公式 高速並列履歴"+(" + netkeiba DB補完" if supplemented else "")
            with _race_history_lock:
                _race_history_jobs[race_id] = {"status":status,"monthsDone":months_done,"maxMonths":max_months,"coverage":cov_now,"error":" | ".join(errors[-5:]),"source":source,"supplementedHorses":supplemented,
                                               "knownCareerStarts":len(required),"fullCareerVerified":verified}
            with _detail_cache_lock:
                _detail_cache.pop(race_id, None)
            try:_build_fast_diagnosis_snapshot(race_id,allow_network=False,deep_context=True)
            except Exception as exc:print("NAR history diagnosis rebuild failed",race_id,exc)
        except Exception as exc:
            errors.append(str(exc))
            cov_now = _history_counts(horse_names, iso_date)
            with _race_history_lock:
                _race_history_jobs[race_id] = {"status":"error","monthsDone":months_done,"maxMonths":max_months,"coverage":cov_now,"error":" | ".join(errors[-5:]),"source":"NAR公式 高速並列履歴"}
    threading.Thread(target=worker, daemon=True).start()
    return dict(job)


def _race_history_status(race_id: str) -> dict | None:
    with _race_history_lock:
        x = _race_history_jobs.get(race_id)
        return dict(x) if x else None


def _nar_attach_recent_batch(detail: dict, limit: int=5, *, DB_PATH, _new_conn) -> dict:
    """Attach recent NAR runs for all horses with one SQL query, avoiding N+1."""
    if not isinstance(detail,dict) or str(detail.get("circuit") or "")!="地方":
        return detail
    horses=detail.get("horses") or []
    names=[str(h.get("name") or "") for h in horses if h.get("name")]
    cutoff=str(detail.get("date") or "9999-12-31")
    if not names or not DB_PATH.exists():return detail
    conn=_new_conn(DB_PATH)
    try:
        ph=",".join("?" for _ in names)
        sql=f"""
        SELECT e.name,e.date,e.track,e.race_no,e.finish,e.time_seconds,e.corner_positions_json,
               e.carried_weight,e.jockey,e.trainer,
               r.title,r.distance,r.weather,r.condition,r.field_size,r.prize1
        FROM entries e
        JOIN races r ON r.track=e.track AND r.date=e.date AND r.race_no=e.race_no
        WHERE e.name IN ({ph}) AND e.date<? AND e.finish>0
        ORDER BY e.name,e.date DESC,e.race_no DESC
        """
        rows=conn.execute(sql,[*names,cutoff]).fetchall()
    finally:
        conn.close()
    grouped={n:[] for n in names}
    for row in rows:
        arr=grouped.get(str(row["name"]) or "")
        if arr is None or len(arr)>=limit:continue
        try:cp=json.loads(row["corner_positions_json"] or "[]")
        except Exception:cp=[]
        arr.append({
            "date":row["date"],"track":row["track"],"raceNumber":int(row["race_no"] or 0),
            "raceId":f"nar-{row['date']}-{row['track']}-{int(row['race_no'] or 0):02d}",
            "title":row["title"] or f"{int(row['race_no'] or 0)}R",
            "distance":int(row["distance"] or 0),"condition":row["condition"] or "不明",
            "weather":row["weather"] or "不明","finish":int(row["finish"] or 0),
            "timeSeconds":float(row["time_seconds"] or 0),"cornerPositions":cp,
            "fieldSize":int(row["field_size"] or 0),"racePrize1":int(row["prize1"] or 0),
            "carriedWeight":float(row["carried_weight"] or 0),
            "jockey":row["jockey"] or "","trainer":row["trainer"] or "",
            "source":"NAR公式ローカル履歴",
        })
    for h in horses:
        h["recentRaces"]=grouped.get(str(h.get("name") or ""),[])[:limit]
        h["allPastRuns"]=list(h["recentRaces"])
    return detail
