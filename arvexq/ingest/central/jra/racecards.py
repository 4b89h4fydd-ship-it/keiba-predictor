"""central/jra/racecards: acquisition behavior preserved from PR #13 (95f2595).

Keyword-only ports are supplied by the application composition root.
This module never imports app or initializes storage/background workers.
"""
from arvexq.ingest.history.run_merge import _jra_history_complete
from arvexq.ingest.history.run_merge import _jra_merge_runs
from arvexq.normalize.central_feed import normalize_central_race
from arvexq.normalize.scalars import _scratch_status
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
import os
import re


from arvexq.ingest.central.jra.state import JRA_BAD_TITLE_RE
from arvexq.ingest.central.jra.state import JRA_CNAME_RE
from arvexq.ingest.central.jra.state import JRA_HORSE_CNAME_RE

def _jra_parse_race(cname: str, supplement_profiles: bool=True, *, _jra_attr_cname, _jra_date_from_cname, _jra_norm_cname, _jra_parse_past_cell, _jra_profile_runs, _jra_program_lookup, _jra_race_no_from_cname, _jra_request, _jra_text, _jra_track_from_cname, _today_iso) -> dict | None:
    date=_jra_date_from_cname(cname); track=_jra_track_from_cname(cname); race_no=_jra_race_no_from_cname(cname)
    cache_sec=int(os.getenv("JRA_LIVE_ODDS_CACHE_SEC","45")) if date==_today_iso() else 600
    try: html=_jra_request("https://www.jra.go.jp/JRADB/accessD.html",cname,cache_sec)
    except Exception:return None
    # The basic dde01 card can omit live fields even while the official dde10
    # card for the same race already contains them. Prefer the official live card.
    if date==_today_iso() and "pw01dde10" not in cname:
        live=[]
        for cc in JRA_CNAME_RE.findall(html):
            cc=_jra_norm_cname(cc)
            if ("pw01dde10" in cc and _jra_date_from_cname(cc)==date and
                _jra_track_from_cname(cc)==track and _jra_race_no_from_cname(cc)==race_no):
                live.append(cc)
        if live:
            cname=live[0]
            try: html=_jra_request("https://www.jra.go.jp/JRADB/accessD.html",cname,0)
            except Exception:pass
    soup=BeautifulSoup(html,"html.parser")
    full=_jra_text(soup)
    if not date or not track or not race_no:return None
    sm=re.search(r"発走時刻[：:]\s*(\d{1,2})時(\d{2})分",full)
    start=f"{int(sm.group(1)):02d}:{sm.group(2)}" if sm else ""
    dm=re.search(r"コース\s*[：:]?\s*([\d,]+)\s*メートル\s*[（(]([^）)]+)[）)]",full)
    distance=int(dm.group(1).replace(",","")) if dm else 0
    course_desc=dm.group(2) if dm else ""
    surface="芝" if "芝" in course_desc else ("ダート" if "ダート" in course_desc else ("障害" if "障" in course_desc else ""))
    weather="不明"; condition="不明"
    wm=re.search(r"天候\s*([^\s]+)",full)
    if wm:weather=wm.group(1)[:4]
    cm=re.search(r"(?:芝|ダート)\s*(良|稍重|重|不良)",full)
    if cm:condition=cm.group(1)
    title=""
    title_block=JRA_BAD_TITLE_RE
    for node in soup.find_all(["h2","h3"]):
        tx=_jra_text(node)
        if not tx or len(tx)>=80 or title_block.search(tx) or "出馬表" in tx:
            continue
        if re.match(r"^\d+レース$",tx):
            continue
        title=tx;break
    if not title:title=f"{race_no}R"
    prize1=0
    pm=re.search(r"1着\s*([\d,.]+)",full)
    if pm:
        try:prize1=int(float(pm.group(1).replace(",",""))*10000)
        except:pass
    horses=[]
    target_table=None
    for table in soup.find_all("table"):
        tx=_jra_text(table.find("thead") or table)
        if "馬番" in tx and "前走" in tx:
            target_table=table;break
    if not target_table:return None
    for tr in target_table.find_all("tr"):
        cells=tr.find_all(["th","td"])
        if len(cells)<4:continue
        # horse number among first 3 cells
        no=0; noidx=-1
        for ci,c in enumerate(cells[:3]):
            mt=re.fullmatch(r"\s*(\d{1,2})\s*",_jra_text(c))
            if mt and 1<=int(mt.group(1))<=18:
                no=int(mt.group(1));noidx=ci;break
        if not no:continue
        frame_no=0
        fm=re.search(r"枠\s*(\d)",_jra_text(cells[0])+" "+str(cells[0]))
        if fm:frame_no=int(fm.group(1))
        # identify horse info and profile cells
        info=None; profile=None; horse_cname=""
        for c in cells:
            hc=_jra_attr_cname(c,JRA_HORSE_CNAME_RE)
            if hc:
                info=c;horse_cname=hc;break
        if info is None:
            info=cells[min(len(cells)-1,noidx+1)]
        info_i=cells.index(info)
        profile=cells[info_i+1] if info_i+1<len(cells) else None
        # horse name from horse profile link or first plausible link/text
        name=""
        for a in info.find_all("a"):
            if _jra_attr_cname(a,JRA_HORSE_CNAME_RE):
                name=_jra_text(a);break
        if not name:
            name=re.split(r"\d+(?:\.\d+)?\(?",_jra_text(info),1)[0].strip()[:40]
        if not name:continue
        infot=_jra_text(info); prot=_jra_text(profile)
        sex="";age=0
        sx=re.search(r"(牡|牝|せん)(\d+)",prot)
        if sx:sex=sx.group(1);age=int(sx.group(2))
        cw=0.0
        cwm=re.search(r"(\d{2}(?:\.\d)?)\s*kg",prot)
        if cwm:cw=float(cwm.group(1))
        jockey=""
        links=[_jra_text(a) for a in profile.find_all("a")] if profile else []
        if links:jockey=links[-1]
        if not jockey and cwm:
            jockey=prot[cwm.end():].strip().split(" ")[0:3]
            jockey=" ".join(jockey).strip()
        trainer=""
        tm=re.search(r"([^\s]+(?:\s[^\s]+)?)\((?:美浦|栗東|本会外)\)",infot)
        if tm:trainer=tm.group(1).strip()
        prize=0
        prm=re.search(r"([\d,.]+)万円",infot)
        if prm:
            try:prize=int(float(prm.group(1).replace(",",""))*10000)
            except:pass
        past=[]
        past_cells=cells[info_i+2:info_i+6]
        for c in past_cells:
            rr=_jra_parse_past_cell(c,date)
            if rr:past.append(rr)
        # JRA card exposes 前走〜4走前. If all four slots were inspected and fewer
        # than four real runs exist, that is the horse's full career to date.
        career_complete=(len(past_cells)>=4 and len(past)<4)
        win_odds=0.0; popularity=0; body_weight=0; body_change=None
        tail=infot.split(name,1)[1] if name in infot else infot
        om=re.search(r"([0-9]+(?:\.[0-9]+)?)\s*\((\d+)番人気\)",tail)
        if om:
            try: win_odds=float(om.group(1)); popularity=int(om.group(2))
            except: pass
        bwm=re.search(r"(\d{3})\s*kg\s*[（(]\s*([+\-]?\d+)\s*[）)]",infot)
        if bwm:
            try: body_weight=int(bwm.group(1)); body_change=int(bwm.group(2))
            except: pass
        elif re.search(r"(\d{3})\s*kg",infot):
            try: body_weight=int(re.search(r"(\d{3})\s*kg",infot).group(1))
            except: pass
        scratch_status=_scratch_status(_jra_text(tr))
        horses.append({"horseNumber":no,"frameNumber":frame_no,"name":name,"age":age,"sex":sex,"carriedWeight":cw,"jockey":jockey,"trainer":trainer,"prizeMoneyAtRace":prize,"recentRaces":past,"winOdds":win_odds or None,"popularity":popularity or None,"bodyWeight":body_weight or None,"bodyWeightChange":body_change,"oddsSource":"JRA公式" if win_odds else "","status":scratch_status,"scratched":bool(scratch_status),"_jraHorseCname":horse_cname,"_jraCareerComplete":career_complete,"jockeyStats":{},"trainerStats":{},"jockeyProfile":{},"trainerProfile":{}})
    if not horses:return None
    program=_jra_program_lookup(date,track,race_no)
    if program:title=program.get("title") or title;distance=int(program.get("distance") or distance);surface=program.get("surface") or surface;start=program.get("startTime") or start
    # Listing must stay fast. Full five-run profile supplementation is done only when needed.
    if supplement_profiles:
        def supplement(h):
            existing=h.get("recentRaces") or []
            if _jra_history_complete(existing,bool(h.get("_jraCareerComplete"))):return h
            extra=_jra_profile_runs(h.get("_jraHorseCname") or "",date,5)
            h["recentRaces"]=_jra_merge_runs(existing,extra,5)
            return h
        workers=max(2,min(8,int(os.getenv("JRA_PROFILE_WORKERS","6"))))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            horses=list(pool.map(supplement,horses))
    rid=f"jra-{date}-{track}-{race_no:02d}"
    return normalize_central_race({"id":rid,"date":date,"track":track,"raceNumber":race_no,"title":title,"distance":distance,"surface":surface,"condition":condition,"weather":weather,"fieldSize":len(horses),"racePrize1":prize1,"startTime":start,"scheduledStartTime":start,"horses":horses,"source":"JRA公式","jraCname":cname})


def _jra_parse_race_summary(cname: str, *, _jra_date_from_cname, _jra_program_lookup, _jra_race_no_from_cname, _jra_request, _jra_text, _jra_track_from_cname, _today_iso) -> dict | None:
    """Fast list-page parser: no horse/profile parsing. Full card loads only when opened."""
    date=_jra_date_from_cname(cname); track=_jra_track_from_cname(cname); race_no=_jra_race_no_from_cname(cname)
    if not date or not track or not race_no:return None
    cache_sec=45 if date==_today_iso() else 900
    try:html=_jra_request("https://www.jra.go.jp/JRADB/accessD.html",cname,cache_sec)
    except Exception:return None
    soup=BeautifulSoup(html,"html.parser"); full=_jra_text(soup)
    sm=re.search(r"発走時刻\s*[：:]?\s*(\d{1,2})時\s*(\d{2})分",full)
    start=f"{int(sm.group(1)):02d}:{sm.group(2)}" if sm else ""
    dm=re.search(r"コース\s*[：:]?\s*([\d,]+)\s*メートル\s*[（(]([^）)]+)[）)]",full)
    distance=int(dm.group(1).replace(",","")) if dm else 0; desc=dm.group(2) if dm else ""
    surface="芝" if "芝" in desc else ("ダート" if "ダート" in desc else ("障害" if "障" in desc else ""))
    weather="不明"; condition="不明"
    wm=re.search(r"天候\s*([^\s]+)",full)
    if wm:weather=wm.group(1)[:4]
    cm=re.search(r"(?:芝|ダート)\s*(良|稍重|重|不良)",full)
    if cm:condition=cm.group(1)
    blocked=JRA_BAD_TITLE_RE
    title=""
    for node in soup.find_all(["h2","h3"]):
        tx=_jra_text(node)
        if not tx or len(tx)>=80 or blocked.search(tx) or "出馬表" in tx or re.match(r"^\d+レース$",tx):continue
        title=tx;break
    if not title:title=f"{race_no}R"
    program=_jra_program_lookup(date,track,race_no)
    if program:title=program.get("title") or title;distance=int(program.get("distance") or distance);surface=program.get("surface") or surface;start=program.get("startTime") or start
    rid=f"jra-{date}-{track}-{race_no:02d}"
    return normalize_central_race({"id":rid,"date":date,"track":track,"raceNumber":race_no,"title":title,"distance":distance,"surface":surface,"condition":condition,"weather":weather,"fieldSize":0,"racePrize1":0,"startTime":start,"scheduledStartTime":start,"horses":[],"source":"JRA公式・高速一覧","jraCname":cname,"_summaryOnly":True})
