"""netkeiba/history: acquisition behavior preserved from PR #13 (95f2595).

Keyword-only ports are supplied by the application composition root.
This module never imports app or initializes storage/background workers.
"""
from arvexq.ingest.parsers.supplemental import _parse_recent_cell
from arvexq.ingest.parsers.supplemental import _safe_int
from arvexq.normalize.scalars import _clean
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed
import os
import re
import time



from arvexq.ingest.supplemental.state import _enrich_data
from arvexq.ingest.supplemental.state import _enrich_data_lock
from arvexq.ingest.supplemental.state import _enrich_jobs
from arvexq.ingest.supplemental.state import _enrich_jobs_lock

def _netkeiba_db_horse_history(name: str, cutoff: str, limit: int=5, *, _netkeiba_get) -> dict:
    """Fallback career lookup by horse name for sparse NAR histories.

    Uses netkeiba DB only as a supplement after NAR official history has been searched.
    The result page contains both central and local starts, which is useful for transfers.
    """
    name=_clean(name)
    if not name:return {"name":"","recentRaces":[]}
    try:
        # netkeiba expects EUC-JP query bytes; UTF-8 silently returns no hits.
        from arvexq.databanks.netkeiba_career import search_url, parse_search
        html=_netkeiba_get(search_url(name),float(os.getenv("NETKEIBA_DB_SEARCH_TIMEOUT_SEC","4.0")),86400)
    except Exception as exc:
        print("netkeiba DB horse search failed",name,exc);return {"name":name,"recentRaces":[]}
    # Exact-name candidates only (absolute links, or a direct redirect to the horse page).
    candidates=[c["id"] for c in parse_search(html,name)]
    best={"name":name,"recentRaces":[]};best_score=-1
    for hid in candidates[:4]:
        try:
            page=_netkeiba_get(f"https://db.netkeiba.com/horse/result/{hid}/",float(os.getenv("NETKEIBA_DB_RESULT_TIMEOUT_SEC","4.0")),86400)
        except Exception as exc:
            print("netkeiba DB horse result failed",name,hid,exc);continue
        ps=BeautifulSoup(page,"html.parser");runs=[]
        for table in ps.find_all("table"):
            trs=table.find_all("tr")
            if not trs:continue
            header_cells=trs[0].find_all(["th","td"])
            headers=[_clean(c.get_text(" ",strip=True)) for c in header_cells]
            # Headers are rendered with spaces ("着 順", "頭 数").
            joined="|".join(re.sub(r"\s+","",h) for h in headers)
            if "日付" not in joined or "着順" not in joined or "距離" not in joined:continue
            def hidx(*keys):
                for i,h in enumerate(headers):
                    hh=re.sub(r"\s+","",h)
                    if any(k in hh for k in keys):return i
                return -1
            i_date=hidx("日付");i_track=hidx("開催");i_title=hidx("レース名");i_field=hidx("頭数")
            i_fin=hidx("着順");i_jockey=hidx("騎手");i_cw=hidx("斤量");i_dist=hidx("距離")
            i_cond=hidx("馬場");i_time=hidx("タイム");i_corner=hidx("通過");i_bw=hidx("馬体重")
            for tr in trs[1:]:
                cells=tr.find_all(["th","td"])
                vals=[_clean(c.get_text(" ",strip=True)) for c in cells]
                def val(i):return vals[i] if i>=0 and i<len(vals) else ""
                dm=re.search(r"(20\d{2})[./](\d{1,2})[./](\d{1,2})",val(i_date))
                if not dm:continue
                date=f"{int(dm.group(1)):04d}-{int(dm.group(2)):02d}-{int(dm.group(3)):02d}"
                if cutoff and date>=cutoff:continue
                fm=re.match(r"\s*(\d+)",val(i_fin))
                if not fm:continue
                dist_txt=val(i_dist);dst=re.search(r"(芝|ダ|障)[^0-9]*(\d{3,4})",dist_txt)
                if not dst:continue
                track=re.sub(r"^\d+|\d+$","",val(i_track)).strip()
                field=_safe_int(val(i_field));corn=[]
                cm=re.search(r"\d{1,2}(?:-\d{1,2})+",val(i_corner))
                if cm:corn=[int(x) for x in cm.group(0).split("-")]
                tm=0.0;mt=re.search(r"(?:(\d+):)?(\d{1,2})\.(\d)",val(i_time))
                if mt:tm=int(mt.group(1) or 0)*60+int(mt.group(2))+int(mt.group(3))/10
                bwm=re.search(r"(\d{3,4})(?:\s*\(\s*([+\-]?\d+)\s*\))?",val(i_bw))
                runs.append({
                    "date":date,"track":track,"title":val(i_title),"distance":int(dst.group(2)),
                    "surface":"障害" if dst.group(1)=="障" else ("芝" if dst.group(1)=="芝" else "ダート"),
                    "condition":val(i_cond) or "不明","weather":"不明","fieldSize":field,
                    "finish":int(fm.group(1)),"timeSeconds":tm,"cornerPositions":corn,
                    "carriedWeight":float(re.search(r"\d+(?:\.\d+)?",val(i_cw)).group()) if re.search(r"\d+(?:\.\d+)?",val(i_cw)) else 0.0,
                    "bodyWeight":int(bwm.group(1)) if bwm else None,
                    "bodyWeightChange":int(bwm.group(2)) if bwm and bwm.group(2) is not None else None,
                    "jockey":val(i_jockey),"source":"netkeiba DB補完",
                })
                if len(runs)>=limit:break
            if runs:break
        runs=sorted(runs,key=lambda z:str(z.get("date") or ""),reverse=True)[:limit]
        # Same-name horses: the current runner is the one with the latest pre-race
        # start, not a retired namesake with a longer record.
        score=(int(runs[0]["date"].replace("-","")) if runs else 0)*1000 + len(runs)
        if score>best_score:
            best_score=score;best={"name":name,"_netkeibaHorseId":hid,"recentRaces":runs,"source":"netkeiba DB補完"}
    return best




def _supplement_sparse_nar_history(race_id: str, names: list[str], cutoff: str, *, _netkeiba_db_horse_history) -> int:
    if not names:return 0
    unique=list(dict.fromkeys([_clean(x) for x in names if _clean(x)]))
    workers=max(2,min(4,int(os.getenv("NETKEIBA_DB_HISTORY_WORKERS","4"))))
    rows=[]
    with ThreadPoolExecutor(max_workers=min(workers,len(unique))) as pool:
        futs={pool.submit(_netkeiba_db_horse_history,name,cutoff,5):name for name in unique}
        for fut in as_completed(futs):
            try:
                z=fut.result() or {}
                if z.get("recentRaces"):rows.append(z)
            except Exception as exc:print("sparse NAR history supplement failed",futs[fut],exc)
    if not rows:return 0
    try:
        with _enrich_data_lock:
            olddata=_enrich_data.get(race_id) or {}
            merged={}
            for rr in (olddata.get("netkeibaRows") or [])+rows:
                key=int(rr.get("horseNumber") or 0) or str(rr.get("name") or "")
                if key:merged[key]=rr
            _enrich_data[race_id]={
                "netkeibaRows":list(merged.values()),
                "smartRows":olddata.get("smartRows") or [],
                "extra":olddata.get("extra") or [],
            }
        with _enrich_jobs_lock:
            prev=_enrich_jobs.get(race_id) or {}
            src=list(prev.get("sources") or [])
            if "netkeiba DB補完" not in src:src.append("netkeiba DB補完")
            _enrich_jobs[race_id]={**prev,"status":"done","sources":src,"finishedAt":time.time()}
    except Exception as exc:
        print("sparse NAR enrichment cache failed",race_id,exc);return 0
    return len(rows)


def _netkeiba_past_rows_fast(detail: dict, *, _netkeiba_get, _netkeiba_race_id, _nk_row_horse) -> list[dict]:
    """One cached page gets recent runs for every JRA starter."""
    rid=str(detail.get("netkeibaRaceId") or "") or _netkeiba_race_id(
        str(detail.get("date") or ""),str(detail.get("track") or ""),int(detail.get("raceNumber") or 0)
    )
    if not rid:return []
    url=f"https://race.netkeiba.com/race/shutuba_past.html?race_id={rid}&rf=shutuba_submenu"
    try:
        html=_netkeiba_get(
            url,
            float(os.getenv("FAST_HISTORY_TIMEOUT_SEC","1.8")),
            int(os.getenv("FAST_HISTORY_CACHE_SEC","300")),
        )
    except Exception as exc:
        print("fast JRA past page failed",rid,exc);return []
    soup=BeautifulSoup(html,"html.parser");out=[]
    for tr in soup.select("tr.HorseList"):
        horse=_nk_row_horse(tr)
        if not horse:continue
        runs=[]
        for td in tr.find_all("td"):
            z=_parse_recent_cell(td.get_text(" ",strip=True))
            if z:runs.append(z)
            if len(runs)>=5:break
        horse["recentRaces"]=runs[:5]
        out.append(horse)
    return out
