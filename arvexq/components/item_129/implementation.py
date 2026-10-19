"""Owned definitions, installed in the original app context by components.runtime.

The migration bridge preserves existing global state, decorators and monkeypatch
contracts. These definitions are not independently initialized modules yet.
"""

def _ensure_race_volatility(detail: dict) -> dict:
    if not isinstance(detail,dict):return detail
    v=detail.get("volatility") or {}
    if v.get("version")!=VOLATILITY_ENGINE_VERSION:
        detail["volatility"]=_race_volatility(detail)
    return detail

def _local_volatility_map(race_ids:list[str])->dict[str,dict]:
    ids=[str(x) for x in race_ids if x]
    if not ids:return {}
    out={}
    # PreparedStore first.
    if PREPARED_DB_PATH.exists():
        conn=sqlite3.connect(PREPARED_DB_PATH,timeout=.25)
        conn.row_factory=sqlite3.Row
        try:
            for start in range(0,len(ids),200):
                chunk=ids[start:start+200]
                ph=",".join("?" for _ in chunk)
                rows=conn.execute(
                    f"SELECT race_id,payload FROM prepared_races WHERE race_id IN ({ph})",
                    chunk
                ).fetchall()
                for row in rows:
                    try:d=json.loads(row["payload"])
                    except Exception:continue
                    d=_ensure_race_volatility(d)
                    v=d.get("volatility") or {}
                    if v.get("version")==VOLATILITY_ENGINE_VERSION:
                        out[str(row["race_id"])]=v
        except sqlite3.Error:
            pass
        finally:
            conn.close()

    missing=[rid for rid in ids if rid not in out]
    if missing and RACEDB_PATH.exists():
        conn=sqlite3.connect(RACEDB_PATH,timeout=.25)
        conn.row_factory=sqlite3.Row
        try:
            for start in range(0,len(missing),200):
                chunk=missing[start:start+200]
                ph=",".join("?" for _ in chunk)
                rows=conn.execute(
                    f"SELECT race_id,payload FROM race_snapshots WHERE race_id IN ({ph})",
                    chunk
                ).fetchall()
                for row in rows:
                    try:d=json.loads(row["payload"])
                    except Exception:continue
                    d=_ensure_race_volatility(d)
                    v=d.get("volatility") or {}
                    if v.get("version")==VOLATILITY_ENGINE_VERSION:
                        out[str(row["race_id"])]=v
        except sqlite3.Error:
            pass
        finally:
            conn.close()
    return out

def _attach_local_volatility_to_summaries(rows:list[dict])->list[dict]:
    if not rows:return rows
    vm=_local_volatility_map([str(r.get("id") or "") for r in rows])
    if not vm:return rows
    out=[]
    for r in rows:
        z=dict(r)
        v=vm.get(str(z.get("id") or ""))
        if v:z["volatility"]=v
        out.append(z)
    return out

def _compute_local_volatility_for_race(race_id:str)->dict|None:
    # Strictly local: no public-site wait. Used by the selected venue's 12-row pack.
    d=_prepared_get_fresh(race_id) or _racedb_get_fast(race_id)
    if d:
        d=_ensure_race_volatility(d)
        v=d.get("volatility") or {}
        if v.get("ready"):return v

    d=_fast_local_race_detail(race_id)
    if not d:return v if 'v' in locals() and v else None
    try:
        if race_id.startswith("nar-"):d=_nar_attach_recent_batch(d,5)
        d=_attach_stored_career(d)
        d=_precompute_detail_metrics(d)
        v=d.get("volatility") or {}
        # Save so the next page/open is zero-wait.
        try:
            PREPARED_STORE.put(d,force=True)
            RACEDB.upsert_race(d)
        except Exception:
            pass
        return v if v.get("version")==VOLATILITY_ENGINE_VERSION else None
    except Exception as exc:
        print("local volatility compute failed",race_id,exc)
        return None
