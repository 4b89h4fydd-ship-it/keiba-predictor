"""Retention for partial odds and stored analysis updates."""
import copy
from contextlib import closing
import json
import sqlite3
from arvexq.storage.policies.snapshots import _merge


def retain_odds(path, race_id, rows):
    with closing(sqlite3.connect(path,timeout=3)) as conn:
        previous=conn.execute('''SELECT o.horse_no,o.win_odds,o.popularity FROM odds_history o
            JOIN (SELECT horse_no,MAX(captured_at) latest FROM odds_history WHERE race_id=? GROUP BY horse_no) x
            ON o.horse_no=x.horse_no AND o.captured_at=x.latest WHERE o.race_id=?''',(race_id,race_id)).fetchall()
    latest={no:{'winOdds':odds,'popularity':pop} for no,odds,pop in previous}
    out=[]
    for row in rows:
        retained=copy.deepcopy(row)
        try:number=int(row.get('horseNumber') or 0)
        except (TypeError,ValueError):number=0
        for key,value in latest.get(number,{}).items():
            if retained.get(key) in (None,'') and value is not None:
                retained[key]=value
        out.append(retained)
    return out


def retain_analysis(path, race_id, payload):
    with closing(sqlite3.connect(path,timeout=3)) as conn:
        row=conn.execute('SELECT raw_json FROM race_analysis WHERE race_id=?',(race_id,)).fetchone()
    if not row:return payload
    try:previous=json.loads(row[0])
    except (TypeError,ValueError):return payload
    return _merge(previous,payload) if isinstance(previous,dict) else payload
