"""racedb/racecards.py: SQL, payload and preservation rules inherited from 19b76d3."""
from __future__ import annotations
import json
import sqlite3
import time
from arvexq.prediction.prerace_archive import sealed_lock as _arvexq_sealed_lock


class RaceCards:
    def upsert_race(self, detail: dict) -> None:
        if not isinstance(detail,dict):return
        race_id=str(detail.get("id") or "").strip()
        if not race_id:return
        now=int(time.time())
        detail=self._ports._strip_excluded(detail)
        conn=sqlite3.connect(self.path,timeout=5)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            old=conn.execute("SELECT payload FROM race_snapshots WHERE race_id=?",(race_id,)).fetchone()
            if old:
                try:previous=json.loads(old[0])
                except Exception:previous={}
                if isinstance(previous.get("preRacePrediction"),dict) and (_arvexq_sealed_lock(previous) or self._ports._prediction_clock_state(detail)[0]=="started" or not isinstance(detail.get("preRacePrediction"),dict)):
                    detail["preRacePrediction"]=previous["preRacePrediction"]
            snapshot_payload=self._ports._compact_display_snapshot(detail)
            payload=json.dumps(snapshot_payload,ensure_ascii=False,separators=(",",":"),default=str)
            conn.execute(
                """INSERT INTO race_snapshots(race_id,race_date,circuit,track,race_no,title,surface,distance,condition,weather,start_time,updated_at,payload)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(race_id) DO UPDATE SET race_date=excluded.race_date,circuit=excluded.circuit,track=excluded.track,
                   race_no=excluded.race_no,title=excluded.title,surface=excluded.surface,distance=excluded.distance,condition=excluded.condition,
                   weather=excluded.weather,start_time=excluded.start_time,updated_at=excluded.updated_at,payload=excluded.payload""",
                (race_id,str(detail.get("date") or ""),str(detail.get("circuit") or ""),str(detail.get("track") or ""),int(detail.get("raceNumber") or 0),
                 str(detail.get("title") or ""),str(detail.get("surface") or ""),int(detail.get("distance") or 0),str(detail.get("condition") or ""),
                 str(detail.get("weather") or ""),str(detail.get("startTime") or ""),now,payload)
            )
            for h in detail.get("horses",[]) or []:
                if not isinstance(h,dict):continue
                no=int(h.get("horseNumber") or 0)
                if no<=0:continue
                hk=self._horse_key(h)
                ped=h.get("pedigree") if isinstance(h.get("pedigree"),dict) else {}
                smart=h.get("smartRc") if isinstance(h.get("smartRc"),dict) else {}
                ext=str(h.get("_jraHorseCname") or h.get("_netkeibaHorseId") or h.get("horseId") or "")
                conn.execute(
                    """INSERT INTO horse_master(horse_key,name,horse_external_id,sex,age,birthday,sire,dam,damsire,trainer,owner,producer,updated_at,raw_json)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                       ON CONFLICT(horse_key) DO UPDATE SET name=excluded.name,horse_external_id=CASE WHEN excluded.horse_external_id<>'' THEN excluded.horse_external_id ELSE horse_master.horse_external_id END,
                       sex=CASE WHEN excluded.sex<>'' THEN excluded.sex ELSE horse_master.sex END,age=CASE WHEN excluded.age>0 THEN excluded.age ELSE horse_master.age END,
                       birthday=CASE WHEN excluded.birthday<>'' THEN excluded.birthday ELSE horse_master.birthday END,sire=CASE WHEN excluded.sire<>'' THEN excluded.sire ELSE horse_master.sire END,
                       dam=CASE WHEN excluded.dam<>'' THEN excluded.dam ELSE horse_master.dam END,damsire=CASE WHEN excluded.damsire<>'' THEN excluded.damsire ELSE horse_master.damsire END,
                       trainer=CASE WHEN excluded.trainer<>'' THEN excluded.trainer ELSE horse_master.trainer END,owner=CASE WHEN excluded.owner<>'' THEN excluded.owner ELSE horse_master.owner END,
                       producer=CASE WHEN excluded.producer<>'' THEN excluded.producer ELSE horse_master.producer END,updated_at=excluded.updated_at,raw_json=excluded.raw_json""",
                    (hk,str(h.get("name") or ""),ext,str(h.get("sex") or ""),int(h.get("age") or 0),str(h.get("birthday") or ""),
                     str(ped.get("sire") or ""),str(ped.get("dam") or ""),str(ped.get("damsire") or ped.get("damSire") or ""),str(h.get("trainer") or ""),
                     str(h.get("owner") or ""),str(h.get("producer") or ""),now,json.dumps(h,ensure_ascii=False,separators=(",",":"),default=str))
                )
                conn.execute(
                    """INSERT INTO horse_entries(race_id,horse_no,horse_key,frame_no,name,jockey,trainer,carried_weight,body_weight,body_weight_change,prize_money,
                       ten1f,ten,agari,estimated_popularity,pedigree_json,style_json,fit_json,debut_json,jump_json,representative_json,opponent_level,metrics_json,sources_json,updated_at,raw_json)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                       ON CONFLICT(race_id,horse_no) DO UPDATE SET horse_key=excluded.horse_key,frame_no=excluded.frame_no,name=excluded.name,jockey=excluded.jockey,
                       trainer=excluded.trainer,carried_weight=excluded.carried_weight,body_weight=excluded.body_weight,body_weight_change=excluded.body_weight_change,
                       prize_money=excluded.prize_money,ten1f=COALESCE(excluded.ten1f,horse_entries.ten1f),ten=COALESCE(excluded.ten,horse_entries.ten),
                       agari=COALESCE(excluded.agari,horse_entries.agari),estimated_popularity=COALESCE(excluded.estimated_popularity,horse_entries.estimated_popularity),
                       pedigree_json=excluded.pedigree_json,style_json=excluded.style_json,fit_json=excluded.fit_json,debut_json=excluded.debut_json,
                       jump_json=excluded.jump_json,representative_json=excluded.representative_json,opponent_level=excluded.opponent_level,
                       metrics_json=excluded.metrics_json,sources_json=excluded.sources_json,updated_at=excluded.updated_at,raw_json=excluded.raw_json""",
                    (race_id,no,hk,int(h.get("frameNumber") or 0),str(h.get("name") or ""),str(h.get("jockey") or ""),str(h.get("trainer") or ""),
                     h.get("carriedWeight"),h.get("bodyWeight"),h.get("bodyWeightChange"),int(h.get("prizeMoneyAtRace") or 0),
                     None if smart.get("ten1f") in (None,"") else str(smart.get("ten1f")),None if smart.get("ten") in (None,"") else str(smart.get("ten")),
                     None if smart.get("agari") in (None,"") else str(smart.get("agari")),None if smart.get("estimatedPopularity") in (None,"") else str(smart.get("estimatedPopularity")),
                     json.dumps(ped,ensure_ascii=False,separators=(",",":"),default=str),
                     json.dumps((h.get("precomputedMetrics") or {}).get("style") or {},ensure_ascii=False,separators=(",",":"),default=str),
                     json.dumps((h.get("precomputedMetrics") or {}).get("fit") or {},ensure_ascii=False,separators=(",",":"),default=str),
                     json.dumps({"isDebut":bool(h.get("debutNoHistory")),"analysisMode":detail.get("analysisMode")},ensure_ascii=False,separators=(",",":")),
                     json.dumps(h.get("jumpStats") or h.get("obstacleStats") or {},ensure_ascii=False,separators=(",",":"),default=str),
                     json.dumps(h.get("representativeRun") or {},ensure_ascii=False,separators=(",",":"),default=str),
                     (h.get("precomputedMetrics") or {}).get("fit",{}).get("level"),
                     json.dumps(h.get("precomputedMetrics") or {},ensure_ascii=False,separators=(",",":"),default=str),
                     json.dumps(detail.get("dataSources") or [],ensure_ascii=False,separators=(",",":"),default=str),now,json.dumps(h,ensure_ascii=False,separators=(",",":"),default=str))
                )
                for rr in (h.get("allPastRuns") or h.get("recentRaces") or []):
                    if not isinstance(rr,dict):continue
                    rk=self._run_key(rr)
                    conn.execute(
                        """INSERT INTO past_runs(horse_key,run_key,race_date,track,title,distance,surface,condition,weather,finish,time_seconds,agari3f,agari_rank,frame_no,horse_no,carried_weight,jockey,corner_json,opponent_level,representative,source,updated_at,raw_json)
                           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                           ON CONFLICT(horse_key,run_key) DO UPDATE SET updated_at=excluded.updated_at,raw_json=excluded.raw_json,
                           agari3f=COALESCE(excluded.agari3f,past_runs.agari3f),agari_rank=COALESCE(excluded.agari_rank,past_runs.agari_rank),
                           opponent_level=COALESCE(excluded.opponent_level,past_runs.opponent_level),representative=MAX(past_runs.representative,excluded.representative)""",
                        (hk,rk,str(rr.get("date") or ""),str(rr.get("track") or ""),str(rr.get("title") or ""),int(rr.get("distance") or 0),str(rr.get("surface") or ""),
                         str(rr.get("condition") or ""),str(rr.get("weather") or ""),int(rr.get("finish") or 0),rr.get("timeSeconds"),rr.get("agari3f") or rr.get("agari"),
                         rr.get("agariRank") or rr.get("agari_rank"),int(rr.get("frameNumber") or 0),int(rr.get("horseNumber") or 0),rr.get("carriedWeight"),str(rr.get("jockey") or ""),
                         json.dumps(rr.get("cornerPositions") or [],ensure_ascii=False,separators=(",",":")),rr.get("opponentLevel"),1 if rr.get("representative") else 0,
                         str(rr.get("source") or ""),now,json.dumps(rr,ensure_ascii=False,separators=(",",":"),default=str))
                    )
            conn.commit()
        finally:
            conn.close()


    def get_race(self, race_id: str) -> tuple[dict | None,int]:
        conn=sqlite3.connect(self.path,timeout=2);conn.row_factory=sqlite3.Row
        try:
            row=conn.execute("SELECT updated_at,payload FROM race_snapshots WHERE race_id=?",(race_id,)).fetchone()
            if not row:return None,0
            try:return json.loads(row["payload"]),int(row["updated_at"] or 0)
            except Exception:return None,0
        finally:conn.close()


    def status(self, race_date: str = "", circuit: str = "") -> dict:
        conn=sqlite3.connect(self.path,timeout=2);conn.row_factory=sqlite3.Row
        try:
            where=[];args=[]
            if race_date:where.append("race_date=?");args.append(race_date)
            if circuit:where.append("circuit=?");args.append(circuit)
            sql="SELECT COUNT(*) cnt,MAX(updated_at) last FROM race_snapshots"+(" WHERE "+" AND ".join(where) if where else "")
            rr=conn.execute(sql,args).fetchone();hm=conn.execute("SELECT COUNT(*) c FROM horse_master").fetchone();pr=conn.execute("SELECT COUNT(*) c FROM past_runs").fetchone();od=conn.execute("SELECT COUNT(*) c FROM odds_history").fetchone();an=conn.execute("SELECT COUNT(*) c FROM race_analysis").fetchone()
            return {"races":int(rr["cnt"] or 0),"last":int(rr["last"] or 0),"horses":int(hm["c"] or 0),"pastRuns":int(pr["c"] or 0),"oddsPoints":int(od["c"] or 0),"analyses":int(an["c"] or 0),"path":str(self.path)}
        finally:conn.close()

