"""Owned definitions, installed in the original app context by components.runtime.

The migration bridge preserves existing global state, decorators and monkeypatch
contracts. These definitions are not independently initialized modules yet.
"""

@app.get("/api/v1/storage-status")
def storage_status():
    p=DATA_ROOT
    return {
        "dataRoot":str(p),
        "persistentLikely":str(p).startswith("/var/data") or str(p).startswith("/data/"),
        "raceDb":str(RACEDB_PATH),
        "preparedDb":str(PREPARED_DB_PATH),
        "narDb":str(DB_PATH),
    }

@app.get("/api/v1/race/{race_id}/version")
def snapshot_version(race_id: str):
    conn=sqlite3.connect(PREPARED_STORE.path,timeout=2)
    try:
        row=conn.execute("SELECT json_extract(payload,'$.preparedMeta.revision'),updated_at FROM prepared_races WHERE race_id=?",(race_id,)).fetchone()
        if not row:raise HTTPException(status_code=404,detail="snapshot not found")
        return {"revision":row[0] or "", "updatedAt":row[1]}
    finally:conn.close()

@app.get("/api/v1/racedb-status")
def racedb_status(date: str = "", circuit: str = ""):
    return {"build":"v302-fullcard-livefix","status":RACEDB.status(date,_clean(circuit)),"dataCoreVersion":ARVEXQ_DATA_CORE_VERSION,"continuousUpdater":True,"trackSpeed":True,"preRaceAudit":True,"safeWinnerLearning":True,"note":"Data Core + T-5分最終固定 + 日付ブロックTRAIN/TUNE/PROMOTION。SHADOWは選定・昇格に使わず監査専用。市場情報はwinner学習に不使用。"}
