"""central/racecards: acquisition behavior preserved from PR #13 (95f2595).

Keyword-only ports are supplied by the application composition root.
This module never imports app or initializes storage/background workers.
"""
from arvexq.infra.pure_snapshots import _merge_official_result
from arvexq.ingest.history.run_merge import _jra_merge_runs
from arvexq.normalize.central_feed import normalize_central_race
import json
import re


from arvexq.ingest.central.jra.state import JRA_BAD_TITLE_RE
from arvexq.ingest.netkeiba.state import _netkeiba_cache
from arvexq.ingest.netkeiba.state import _netkeiba_cache_lock

def central_race_summaries(iso_date: str, allow_network: bool=False, force: bool=False, *, CENTRAL_DB_PATH, CentralStore, _jra_program_summaries, _netkeiba_race_summaries, _new_conn) -> list[dict]:
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
                if res and (res.get("finishers") or res.get("status")=="確定"):q["result"]={"status":res.get("status") or "確定","finishers":res.get("finishers") or [{"finish":1}]}
                else:q["result"]=None
                db.append(q)
        finally:conn.close()
    valid=[x for x in db if not JRA_BAD_TITLE_RE.search(str(x.get("title") or "")) and int(x.get("distance") or 0)>0]
    merged={(str(r.get("track") or ""),int(r.get("raceNumber") or 0)):dict(r) for r in valid}
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
        for r in fresh:
            key=(str(r.get("track") or ""),int(r.get("raceNumber") or 0))
            if not key[0] or not key[1]:continue
            old=merged.get(key,{})
            z=dict(old)
            # Keep rich cached horses/result, but replace stale schedule fields with fresh schedule data.
            for k,v in r.items():
                if k in {"horses","result"}:continue
                if v not in (None,"",0,[]):z[k]=v
            if old.get("result"):z["result"]=old.get("result")
            if old.get("horses"):z["horses"]=[]
            merged[key]=normalize_central_race(z) or z
        if fresh:
            try:
                st=CentralStore();st.upsert(list(merged.values()));st.conn.close()
            except Exception as exc:print("central summary cache save failed",exc)
    out=list(merged.values());out.sort(key=lambda x:(str(x.get("track") or ""),int(x.get("raceNumber") or 0)))
    return out


def central_race_detail(race_id: str, *, CENTRAL_DB_PATH, CentralStore, _central_recent_from_store, _jra_find_cname, _jra_parse_race, _jra_parse_result, _jra_program_lookup, _jra_result_cname_from_card, _merge_central_recent, _netkeiba_current_result, _netkeiba_detail_rows, _netkeiba_program_race_id, _netkeiba_race_meta, _new_conn, _race_should_have_result) -> dict | None:
    detail=None
    if CENTRAL_DB_PATH.exists():
        conn=_new_conn(CENTRAL_DB_PATH)
        try:
            row=conn.execute("SELECT payload FROM central_races WHERE id=?",(race_id,)).fetchone()
            if row:
                try:detail=json.loads(row["payload"])
                except Exception as exc:print("central payload decode failed",race_id,exc)
        finally:conn.close()
    if detail is None:
        mm=re.match(r"^jra-(20\d{2}-\d{2}-\d{2})-([^\-]+)-(\d{2})$",str(race_id or ""))
        if mm:
            detail=_jra_program_lookup(mm.group(1),mm.group(2),int(mm.group(3)))
            if detail:
                detail["id"]=race_id
                try:st=CentralStore();st.upsert([detail]);st.conn.close()
                except Exception as exc:print("central fallback cache save failed",exc)
    if detail is None:return None
    date=str(detail.get("date") or "");track=str(detail.get("track") or "");race_no=int(detail.get("raceNumber") or 0)
    program=_jra_program_lookup(date,track,race_no)
    if program:
        for k in ("title","distance","surface","startTime","scheduledStartTime","meetingNumber","meetingDay","netkeibaRaceId"):
            v=program.get(k)
            if v not in (None,"",0):detail[k]=v
    if not detail.get("netkeibaRaceId"):detail["netkeibaRaceId"]=_netkeiba_program_race_id(date,track,race_no)
    cname=str(detail.get("jraCname") or "")
    should_result=_race_should_have_result(detail)
    if not cname and (should_result or not (detail.get("horses") or []) or int(detail.get("distance") or 0)<=0):
        cname=_jra_find_cname(date,track,race_no)
        if cname:detail["jraCname"]=cname
    # Finished race: fetch JRA official result first. This also supplies exact weather/going.
    if should_result and cname:
        try:
            rc=str(detail.get("resultCname") or "") or _jra_result_cname_from_card(cname)
            if rc:
                official=_jra_parse_result(rc,detail)
                if official:detail=_merge_official_result(detail,official)
        except Exception as exc:print("JRA official result hydrate failed",race_id,exc)
    # Official JRA card is primary for the pre-race card and live body data.
    malformed=(not (detail.get("horses") or []) or bool(JRA_BAD_TITLE_RE.search(str(detail.get("title") or ""))) or int(detail.get("distance") or 0)<=0)
    if cname:
        try:
            live=_jra_parse_race(cname,supplement_profiles=False)
            if live:
                if malformed:
                    # Keep any official result already obtained, but replace the card with the official entry data.
                    saved_result=detail.get("result");saved_rc=detail.get("resultCname")
                    detail=live
                    if saved_result:detail["result"]=saved_result
                    if saved_rc:detail["resultCname"]=saved_rc
                else:
                    for k in ("title","distance","surface","condition","weather","fieldSize","startTime","scheduledStartTime"):
                        v=live.get(k)
                        if v not in (None,"",0,"不明"):detail[k]=v
                    by_no={int(h.get("horseNumber") or 0):h for h in live.get("horses",[]) or []}
                    for h in detail.get("horses",[]) or []:
                        z=by_no.get(int(h.get("horseNumber") or 0))
                        if z:
                            for k in ("bodyWeight","bodyWeightChange","sex","age","carriedWeight","jockey","trainer"):
                                if z.get(k) not in (None,"",0,[]):h[k]=z.get(k)
                            if z.get("recentRaces"):
                                h["recentRaces"]=_jra_merge_runs(h.get("recentRaces") or [],z.get("recentRaces") or [],5)
        except Exception as exc:print("JRA official card hydrate failed",race_id,exc)
    # If the official card is unavailable (e.g. publication ended), fill missing card rows from netkeiba.
    if not (detail.get("horses") or []):
        try:
            nr=_netkeiba_detail_rows(detail)
            if nr:
                for h in nr:
                    h.pop("winOdds",None);h.pop("popularity",None);h.pop("oddsSource",None)
                detail["horses"]=nr;detail["fieldSize"]=len(nr);detail.setdefault("dataSources",[])
                if "netkeiba" not in detail["dataSources"]:detail["dataSources"].append("netkeiba")
        except Exception as exc:print("central card fallback failed",race_id,exc)
    # Before official results exist, fill only missing weather/going from a secondary public race page.
    if detail.get("condition") in (None,"","不明") or detail.get("weather") in (None,"","不明"):
        try:
            meta=_netkeiba_race_meta(detail)
            for k in ("title","distance","condition","weather","startTime"):
                if detail.get(k) in (None,"",0,"不明") and meta.get(k) not in (None,"",0,"不明"):detail[k]=meta[k]
        except Exception as exc:print("central race meta fallback failed",race_id,exc)
    # Result fallback only if JRA official result link was not available yet.
    if should_result and not (detail.get("result") and (detail.get("result") or {}).get("finishers")):
        try:
            rr=_netkeiba_current_result(detail)
            if rr:
                for f in rr.get("finishers",[]) or []:f.pop("winOdds",None)
                detail["result"]=rr
                # Populate result/body fields without odds.
                hs=detail.get("horses") or [];by_no={int(h.get("horseNumber") or 0):h for h in hs}
                for f in rr.get("finishers",[]) or []:
                    h=by_no.get(int(f.get("horseNumber") or 0))
                    if h:
                        for k in ("bodyWeight","bodyWeightChange"):
                            if f.get(k) not in (None,""):h[k]=f.get(k)
        except Exception as exc:print("central result fallback failed",race_id,exc)
    detail.pop("oddsSource",None);detail.pop("oddsType",None);detail.pop("oddsUpdatedAt",None)
    for h in detail.get("horses",[]) or []:
        h.pop("winOdds",None);h.pop("popularity",None);h.pop("oddsSource",None)
    if detail.get("horses") or detail.get("result"):
        try:st=CentralStore();st.upsert([detail]);st.conn.close()
        except Exception as exc:print("central hydrated cache save failed",exc)
    cutoff=str(detail.get("date") or "9999-12-31")
    for h in detail.get("horses",[]) or []:
        try:
            stored=_central_recent_from_store(str(h.get("name") or ""),cutoff,5)
            h["recentRaces"]=_merge_central_recent(h.get("recentRaces") or [],stored,cutoff,5)
        except Exception as exc:
            print("central horse history merge failed",race_id,h.get("name"),exc)
            h["recentRaces"]=[x for x in (h.get("recentRaces") or []) if isinstance(x,dict)][:5]
    return detail
