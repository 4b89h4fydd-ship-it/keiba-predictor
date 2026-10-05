#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from arvexq.prediction.mass_feature_snapshot import build_mass_feature_snapshot
from arvexq.prediction.mass_training_store import load_frozen_training_rows


def horse(no,finish_history,speed):
    return {
        "horseNumber":no,
        "name":f"H{no}",
        "winOdds":2.0+no,
        "popularity":no,
        "recentRaces":[
            {"finish":fin,"fieldSize":10,"distance":1600,"track":"T","surface":"芝","condition":"良","speedIndex":speed-i}
            for i,fin in enumerate(finish_history)
        ],
    }


def confirmed_detail(race_id,date):
    pre={
        "id":race_id,"date":date,"circuit":"中央","track":"T","raceNumber":11,
        "distance":1600,"surface":"芝","condition":"良","preRacePrediction":{"modelVersion":"lock"},
        "horses":[horse(1,[1,2,3,2,1],105),horse(2,[3,3,2,4,2],99),horse(3,[6,5,4,5,3],92),horse(4,[8,7,6,6,5],87)],
    }
    snapshot=build_mass_feature_snapshot(pre)
    final=dict(pre)
    final["massFeatureSnapshot"]=snapshot
    final["result"]={"status":"確定","finishers":[
        {"horseNumber":2,"finish":1},{"horseNumber":1,"finish":2},{"horseNumber":3,"finish":3},{"horseNumber":4,"finish":4},
    ]}
    return final


with tempfile.TemporaryDirectory() as td:
    db=Path(td)/"races.sqlite3"
    conn=sqlite3.connect(db)
    conn.execute("CREATE TABLE race_snapshots(race_id TEXT PRIMARY KEY,race_date TEXT,circuit TEXT,payload TEXT)")
    good=confirmed_detail("R1","2026-10-01")
    no_frozen=dict(good);no_frozen["id"]="R2";no_frozen.pop("massFeatureSnapshot",None)
    not_final=confirmed_detail("R3","2026-10-03");not_final["result"]["status"]="速報"
    for row in (good,no_frozen,not_final):
        conn.execute("INSERT INTO race_snapshots VALUES(?,?,?,?)",(row["id"],row["date"],row["circuit"],json.dumps(row,ensure_ascii=False)))
    conn.commit();conn.close()
    rows=load_frozen_training_rows(db)

assert len(rows)==4,len(rows)
assert {r["raceId"] for r in rows}=={"R1"}
assert sum(r["labelWin"] for r in rows)==1
winner=next(r for r in rows if r["labelWin"]==1)
assert winner["horseNumber"]==2
assert all(r.get("featureHash") for r in rows)
print("mass-training-store-ok",len(rows),winner["horseNumber"])
