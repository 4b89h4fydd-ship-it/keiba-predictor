"""Owned definitions, installed in the original app context by components.runtime.

The migration bridge preserves existing global state, decorators and monkeypatch
contracts. These definitions are not independently initialized modules yet.
"""

@app.get("/api/v1/race/{race_id}/horse/{horse_no}")
def horse_snapshot(race_id: str, horse_no: int):
    conn=sqlite3.connect(PREPARED_STORE.path,timeout=2)
    try:
        row=conn.execute("SELECT payload FROM horse_snapshots WHERE race_id=? AND horse_no=?",(race_id,horse_no)).fetchone()
        if not row:raise HTTPException(status_code=404,detail="horse snapshot not found")
        return json.loads(row[0])
    finally:conn.close()
