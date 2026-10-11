"""snapshots/local: original PR #13 acquisition orchestration.

Storage, evaluation and provider callbacks are explicit keyword-only ports.
Worker behavior, source priority and immutable prediction handling are preserved.
"""
from arvexq.normalize.scalars import _scratch_status
from arvexq.normalize.scalars import _stable_id
import json
import re
import time


def _fast_local_race_detail(race_id: str, *, CENTRAL_DB_PATH, DB_PATH, RACEDB, _new_conn) -> dict | None:
    """First paint from local DB only. Never wait on web/history/profile lookups."""
    now=int(time.time())
    if race_id.startswith("nar-"):
        m=re.match(r"^nar-(\d{4}-\d{2}-\d{2})-(.+)-(\d{2})$",race_id)
        if not m or not DB_PATH.exists():return None
        iso_date,track,race_no=m.group(1),m.group(2),int(m.group(3))
        conn=_new_conn(DB_PATH)
        try:
            race=conn.execute("SELECT * FROM races WHERE track=? AND date=? AND race_no=?",(track,iso_date,race_no)).fetchone()
            if not race:return None
            entries=conn.execute("SELECT * FROM entries WHERE track=? AND date=? AND race_no=? ORDER BY horse_no",(track,iso_date,race_no)).fetchall()
        finally:conn.close()
        if not entries:return None
        horses=[];finishers=[]
        for e in entries:
            horses.append({"id":_stable_id(iso_date,track,race_no,e["horse_no"],e["name"]),
                "horseNumber":int(e["horse_no"]),"frameNumber":int(e["frame_no"] or 0),"name":e["name"],
                "age":int(e["age"] or 0),"sex":e["sex"] or "牡","carriedWeight":float(e["carried_weight"] or 0),
                "jockey":e["jockey"] or "","trainer":e["trainer"] or "",
                "status":str(e["status"] or "") if "status" in e.keys() else "",
                "scratched":bool(_scratch_status(str(e["status"] or ""))) if "status" in e.keys() else False,
                "recentRaces":[],
                "jockeyStats":{},"trainerStats":{},"jockeyProfile":{},"trainerProfile":{},
                "collectionState":{"status":"basic","history":"loading","pastRunCount":0}})
            fin=int(e["finish"] or 0)
            if fin>0:
                try:cp=json.loads(e["corner_positions_json"] or "[]")
                except Exception:cp=[]
                finishers.append({"finish":fin,"horseNumber":int(e["horse_no"]),"frameNumber":int(e["frame_no"] or 0),
                                  "name":e["name"],"timeSeconds":float(e["time_seconds"] or 0),"cornerPositions":cp})
        finishers.sort(key=lambda x:(x["finish"],x["horseNumber"]))
        need=min(3,len(entries));ranks={x["finish"] for x in finishers}
        finalized=need>0 and all(i in ranks for i in range(1,need+1))
        detail={"id":race_id,"circuit":"地方","date":iso_date,"track":track,"raceNumber":race_no,
                "title":race["title"] or f"{race_no}R","distance":int(race["distance"] or 0),
                "condition":race["condition"] or "不明","weather":race["weather"] or "不明",
                "fieldSize":int(race["field_size"] or len(entries)),"racePrize1":int(race["prize1"] or 0),
                "surface":"","startTime":race["start_time"] or "",
                "scheduledStartTime":race["scheduled_start_time"] or race["start_time"] or "",
                "horses":horses,"result":{"status":"確定","finishers":finishers} if finalized else None,
                "source":"NAR公式・高速Snapshot"}
    else:
        if not CENTRAL_DB_PATH.exists():return None
        conn=_new_conn(CENTRAL_DB_PATH)
        try:row=conn.execute("SELECT payload FROM central_races WHERE id=?",(race_id,)).fetchone()
        finally:conn.close()
        if not row:return None
        try:detail=json.loads(row["payload"])
        except Exception:return None
        if not isinstance(detail,dict) or not (detail.get("horses") or []):return None
        detail=dict(detail);detail["id"]=race_id
        for h in detail.get("horses",[]) or []:
            if not isinstance(h,dict):continue
            runs=list(h.get("recentRaces") or h.get("allPastRuns") or [])[:5]
            h["recentRaces"]=runs;h.pop("allPastRuns",None)
            h.setdefault("jockeyStats",{});h.setdefault("trainerStats",{})
            h.setdefault("jockeyProfile",{});h.setdefault("trainerProfile",{})
            h["collectionState"]={"status":"complete" if runs else "basic",
                                  "history":"available" if runs else "loading","pastRunCount":len(runs)}
        detail["source"]=str(detail.get("source") or "JRA")+"・高速Snapshot"
    try:
        latest=RACEDB.odds_latest(race_id);by={int(x.get("horseNumber") or 0):x for x in latest}
        for h in detail.get("horses",[]) or []:
            z=by.get(int(h.get("horseNumber") or 0))
            if z:
                if z.get("winOdds") is not None:h["winOdds"]=z["winOdds"]
                if z.get("popularity") is not None:h["popularity"]=z["popularity"]
    except Exception:pass
    title=str(detail.get("title") or "");surface=str(detail.get("surface") or "")
    detail["analysisMode"]="障害" if (surface=="障害" or "障害" in title or "ジャンプ" in title) else ("新馬" if re.search(r"(?:新馬|メイクデビュー)",title) else "平地")
    try:
        saved_analysis=RACEDB.get_analysis(race_id)
        if saved_analysis:detail["analysis"]=saved_analysis
    except Exception:pass
    detail["preparedMeta"]={"prepared":True,"fastPartial":True,"preparedAtEpoch":now,"build":"v93-fast"}
    return detail
