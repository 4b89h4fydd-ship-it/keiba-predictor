"""Owned definitions, installed in the original app context by components.runtime.

The migration bridge preserves existing global state, decorators and monkeypatch
contracts. These definitions are not independently initialized modules yet.
"""

def nar_race_summaries(iso_date: str) -> list[dict]:
    if not DB_PATH.exists():
        return []
    conn = _new_conn(DB_PATH)
    try:
        rows = conn.execute(
            """
            SELECT r.*,
                   COUNT(e.horse_no) AS entry_count,
                   SUM(CASE WHEN e.finish=1 THEN 1 ELSE 0 END) AS f1,
                   SUM(CASE WHEN e.finish=2 THEN 1 ELSE 0 END) AS f2,
                   SUM(CASE WHEN e.finish=3 THEN 1 ELSE 0 END) AS f3
            FROM races r
            LEFT JOIN entries e ON e.track=r.track AND e.date=r.date AND e.race_no=r.race_no
            WHERE r.date=?
            GROUP BY r.track,r.date,r.race_no
            ORDER BY r.track,r.race_no
            """,
            (iso_date,),
        ).fetchall()
        # Same official SQLite entry store as the existing race detail.
        # Never publish synthetic [{"finish":1}] placeholders as results.
        entry_rows=conn.execute(
            """SELECT track,race_no,horse_no,frame_no,name,finish,time_seconds,corner_positions_json
               FROM entries WHERE date=? AND finish>0 ORDER BY track,race_no,finish,horse_no""",
            (iso_date,),
        ).fetchall()
        real_finishers={}
        for e in entry_rows:
            key=(str(e["track"]),int(e["race_no"]))
            try: corners=json.loads(e["corner_positions_json"] or "[]")
            except (ValueError,TypeError): corners=[]
            real_finishers.setdefault(key,[]).append({
                "finish":int(e["finish"]),"horseNumber":int(e["horse_no"]),
                "frameNumber":int(e["frame_no"] or 0),"name":e["name"] or "",
                "timeSeconds":float(e["time_seconds"] or 0),
                "cornerPositions":corners if isinstance(corners,list) else [],
            })
        out=[]
        for r in rows:
            count=int(r["entry_count"] or r["field_size"] or 0)
            finalized=count>0 and int(r["f1"] or 0)>0 and int(r["f2"] or 0)>0 and (count<3 or int(r["f3"] or 0)>0)
            out.append({
                "id":f"nar-{iso_date}-{r['track']}-{int(r['race_no']):02d}",
                "circuit":"地方","date":iso_date,"track":r["track"],"raceNumber":int(r["race_no"]),
                "title":r["title"] or f"{int(r['race_no'])}R","distance":int(r["distance"] or 0),
                "condition":r["condition"] or "不明","weather":r["weather"] or "不明",
                "fieldSize":count,"racePrize1":int(r["prize1"] or 0),"surface":"",
                "startTime":r["start_time"] or "","scheduledStartTime":r["scheduled_start_time"] or r["start_time"] or "",
                "startTimeChanged":bool((r["scheduled_start_time"] or "") and (r["start_time"] or "") and r["scheduled_start_time"]!=r["start_time"]),
                "horses":[],"result":{"status":"確定","finishers":real_finishers.get((str(r["track"]),int(r["race_no"])),[])} if finalized else None,"source":"NAR公式"
            })
        return [row for row in out if str(row.get("track") or "") not in ("帯広", "帯広ば")]
    finally:
        conn.close()

def central_race_summaries(iso_date: str, allow_network: bool = False, force: bool = False) -> list[dict]:
    db=[]
    if CENTRAL_DB_PATH.exists():
        conn=_new_conn(CENTRAL_DB_PATH)
        try:
            rows=conn.execute("SELECT payload FROM central_races WHERE date=? ORDER BY track,race_no",(iso_date,)).fetchall()
            for x in rows:
                try:r=json.loads(x["payload"])
                except Exception:continue
                hs=r.get("horses") if isinstance(r.get("horses"),list) else [];q=dict(r);q["fieldSize"]=int(q.get("fieldSize") or len(hs));q["horses"]=[]
                if JRA_BAD_TITLE_RE.search(str(q.get("title") or "")):q["title"]=f"{int(q.get('raceNumber') or 0)}R"
                res=q.get("result") if isinstance(q.get("result"),dict) else None
                if res and (res.get("finishers") or res.get("status")=="確定"):q["result"]={"status":res.get("status") or "確定","finishers":res.get("finishers") or []}
                else:q["result"]=None
                db.append(q)
        finally:conn.close()
    valid=[x for x in db if not JRA_BAD_TITLE_RE.search(str(x.get("title") or "")) and int(x.get("distance") or 0)>0]
    merged=_index_race_summaries(valid)
    tracks={k[0] for k in merged if k[0]}
    # A normal JRA day has multiple venues. If the cache is clearly complete, return instantly.
    complete=len(merged)>=20 and len(tracks)>=2
    if allow_network and (force or not complete):
        program=[]; nk=[]
        try:program=_jra_program_summaries(iso_date)
        except Exception as exc:print("JRA program list failed",iso_date,exc)
        # Program page is the fast authoritative schedule. Netkeiba fills gaps and provides race ids.
        if len(program)<20 or len({str(r.get('track') or '') for r in program})<2:
            try:nk=_netkeiba_race_summaries(iso_date)
            except Exception as exc:print("netkeiba summary fallback failed",iso_date,exc)
        else:
            # Reuse netkeiba only from its short in-memory cache when available; avoid a second wait.
            try:
                token=iso_date.replace('-','');url=f"https://race.netkeiba.com/top/race_list_sub.html?kaisai_date={token}"
                with _netkeiba_cache_lock:
                    hit=_netkeiba_cache.get(url)
                if hit:nk=_netkeiba_race_summaries(iso_date)
            except Exception:pass
        fresh=list(program or [])+list(nk or [])
        merged=_merge_race_summaries(merged,fresh,normalize_central_race)
        if fresh:
            try:
                st=CentralStore();st.upsert(list(merged.values()));st.conn.close()
            except Exception as exc:print("central summary cache save failed",exc)
    out=list(merged.values());out.sort(key=lambda x:(str(x.get("track") or ""),int(x.get("raceNumber") or 0)))
    return out

@app.get("/api/v1/races")
def races(date: str = Query(...), circuit: str = Query(""), force: int = Query(0), bundle: int = Query(0)):
    circuit=_clean(circuit)
    now=time.time();ck=f"{date}|{circuit or 'all'}"
    with _race_list_cache_lock:
        hit=_race_list_cache.get(ck)
        if hit and not force and ((hit[1] and date<_today_iso()) or now-hit[0]<15):
            cached_rows=_attach_local_volatility_to_summaries([x for x in (hit[1] or []) if str(x.get("track") or "") not in ("帯広", "帯広ば")])
            if circuit:
                return {"races":cached_rows,"prepared":_local_starter_bundle(cached_rows)} if bundle else cached_rows
            has_central=any(str(x.get("circuit") or "")=="中央" for x in cached_rows)
            has_local=any(str(x.get("circuit") or "")=="地方" for x in cached_rows)
            if date<_today_iso() or (has_central and has_local):
                return {"races":cached_rows,"prepared":_local_starter_bundle(cached_rows)} if bundle else cached_rows
        if force:_race_list_cache.pop(ck,None)
    rows=[]
    if circuit in ("","地方"):
        try:
            nar_rows=nar_race_summaries(date)
        except Exception as exc:
            print(f"NAR summary read failed: {exc}");nar_rows=[]
        rows.extend(nar_rows)
        if force or not nar_rows:_schedule_live_refresh(date, force=bool(force))
    if circuit in ("","中央"):
        try:
            crows=central_race_summaries(date,allow_network=False,force=False)
        except Exception as exc:
            print(f"Central summary read failed: {exc}");crows=[]
        rows.extend(crows)
        if force or not crows:_schedule_central_refresh(date,force=bool(force))
    rows=[x for x in rows if str(x.get("track") or "") not in ("帯広", "帯広ば")]
    rows=_attach_local_volatility_to_summaries(rows)
    if date==_today_iso():
        for circuit_name in ("中央","地方"):
            for track_name in sorted({str(x.get("track") or "") for x in rows if str(x.get("circuit") or "")==circuit_name}):
                if not track_name:continue
                subset=[x for x in rows if str(x.get("circuit") or "")==circuit_name and str(x.get("track") or "")==track_name]
                if any(str(x.get("weather") or "不明")=="不明" or str(x.get("condition") or "不明")=="不明" for x in subset):
                    _schedule_track_environment(date,circuit_name,track_name,False)
    with _race_list_cache_lock:
        _race_list_cache[ck]=(now,rows)
        if len(_race_list_cache)>24:
            oldest=min(_race_list_cache.items(),key=lambda kv:kv[1][0])[0];_race_list_cache.pop(oldest,None)
    return {"races":rows,"prepared":_local_starter_bundle(rows)} if bundle else rows

@app.get("/api/v1/track-pack")
def track_pack(date: str = Query(...), circuit: str = Query(...), track: str = Query(...), fill: int = Query(1)):
    """Return venue snapshots from local DB only; fill local-only gaps for instant taps."""
    out=[]
    seen=set()

    # Prepared store first.
    if PREPARED_DB_PATH.exists():
        conn=sqlite3.connect(PREPARED_DB_PATH,timeout=.35)
        conn.row_factory=sqlite3.Row
        try:
            rows=conn.execute(
                "SELECT race_id,payload FROM prepared_races WHERE race_date=? AND circuit=? ORDER BY race_id",
                (date,circuit),
            ).fetchall()
            for row in rows:
                try:d=json.loads(row["payload"])
                except Exception:continue
                if str(d.get("track") or "")!=track:continue
                if not (d.get("horses") or []):continue
                rid=str(d.get("id") or row["race_id"] or "")
                if not rid or rid in seen:continue
                d=_restore_saved_odds(_ensure_race_volatility(d));seen.add(rid);out.append(_compact_display_snapshot(d))
        finally:
            conn.close()

    # RaceDB fills any gaps without network access.
    if RACEDB_PATH.exists():
        conn=sqlite3.connect(RACEDB_PATH,timeout=.35)
        conn.row_factory=sqlite3.Row
        try:
            rows=conn.execute(
                "SELECT race_id,payload FROM race_snapshots WHERE race_date=? AND circuit=? AND track=? ORDER BY race_no",
                (date,circuit,track),
            ).fetchall()
            for row in rows:
                rid=str(row["race_id"] or "")
                if not rid or rid in seen:continue
                try:d=json.loads(row["payload"])
                except Exception:continue
                if not (d.get("horses") or []):continue
                d=_restore_saved_odds(_ensure_race_volatility(d));seen.add(rid);out.append(_compact_display_snapshot(d))
        except sqlite3.OperationalError:
            pass
        finally:
            conn.close()

    # Fill missing races from local stores only. This path never waits on public sites.
    if fill:
        try:
            summaries=nar_race_summaries(date) if circuit=="地方" else central_race_summaries(date,allow_network=False)
        except Exception:
            summaries=[]
        targets=[r for r in summaries if str(r.get("track") or "")==str(track) and r.get("id")]
        missing=[str(r.get("id") or "") for r in targets if str(r.get("id") or "") not in seen]
        def build_local(rid):
            try:
                d=_fast_local_race_detail(rid)
                if not d:
                    _schedule_fast_card_refresh(rid,25)
                    return None
                d=_restore_saved_odds(d)
                d=_ensure_race_volatility(d)
                return _compact_display_snapshot(d)
            except Exception as exc:
                print("track-pack local fill failed",rid,exc)
                return None
        workers=max(1,min(4,len(missing))) if missing else 0
        if workers:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                for d in pool.map(build_local,missing):
                    if d and d.get("id"):
                        rid=str(d.get("id"))
                        if rid not in seen:
                            seen.add(rid)
                            out.append(d)
                            _schedule_fast_card_refresh(rid,35+int(d.get("raceNumber") or 0))
    out.sort(key=lambda d:int(d.get("raceNumber") or 0))
    return {"track":track,"date":date,"circuit":circuit,"races":out,"count":len(out),"source":"local-only","filled":bool(fill)}
