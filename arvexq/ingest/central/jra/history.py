"""central/jra/history: acquisition behavior preserved from PR #13 (95f2595).

Keyword-only ports are supplied by the application composition root.
This module never imports app or initializes storage/background workers.
"""
from arvexq.normalize.scalars import _int
from bs4 import BeautifulSoup
import base64
import re


from arvexq.ingest.central.jra.state import JRA_RESULT_CNAME_RE
from arvexq.ingest.central.jra.state import JRA_TRACK_CODES

def _jra_parse_past_cell(cell, cutoff: str, *, _jra_attr_cname, _jra_iso_date, _jra_parse_time_seconds, _jra_text) -> dict | None:
    txt=_jra_text(cell)
    dm=re.search(r"(20\d{2})年(\d{1,2})月(\d{1,2})日",txt)
    if not dm:return None
    iso=_jra_iso_date(int(dm.group(1)),int(dm.group(2)),int(dm.group(3)))
    if cutoff and iso>=cutoff:return None
    track=""
    for t in list(JRA_TRACK_CODES.values())+["門別","盛岡","水沢","浦和","船橋","大井","川崎","金沢","笠松","名古屋","園田","姫路","高知","佐賀"]:
        if re.search(r"(?:日|\s)"+re.escape(t)+r"(?:\s|$)",txt): track=t;break
    finish=0
    fm=re.search(r"(?<!\d)(\d{1,2})\s*着(?!\d)",txt)
    if fm: finish=int(fm.group(1))
    field=0
    fsm=re.search(r"(\d{1,2})\s*頭",txt)
    if fsm: field=int(fsm.group(1))
    dist=0; surface=""
    dsm=re.search(r"(\d{3,4})(芝|ダ|障)",txt)
    if dsm: dist=int(dsm.group(1)); surface=dsm.group(2)
    cond="不明"
    for c in ["不良","稍重","重","良"]:
        if c in txt: cond=c;break
    weight=0.0
    wm=re.search(r"(\d{2}(?:\.\d)?)\s*kg",txt)
    if wm: weight=float(wm.group(1))
    corners=[]
    for li in cell.find_all("li"):
        z=_jra_text(li)
        if re.fullmatch(r"\d{1,2}",z): corners.append(int(z))
    result_cname=_jra_attr_cname(cell,JRA_RESULT_CNAME_RE)
    rid=("jraresult-"+base64.urlsafe_b64encode(result_cname.encode()).decode().rstrip("=")) if result_cname else ""
    # title is best-effort: text between track and class/finish data
    title=""
    if track:
        after=txt.split(track,1)[1].strip()
        after=re.split(r"\s+(?:\d{1,2}着|\d{1,2}頭|\d+番)",after,1)[0]
        title=after[:60].strip()
    tm=_jra_parse_time_seconds(txt)
    return {"date":iso,"track":track,"title":title,"distance":dist,"surface":surface,"condition":cond,"weather":"不明","fieldSize":field,"finish":finish,"timeSeconds":tm,"cornerPositions":corners,"carriedWeight":weight,"raceId":rid,"source":"JRA公式"}


def _jra_profile_runs(cname: str, cutoff: str, limit: int=5, *, _jra_attr_cname, _jra_iso_date, _jra_parse_time_seconds, _jra_request, _jra_text) -> list[dict]:
    if not cname:return []
    try: html=_jra_request("https://www.jra.go.jp/JRADB/accessU.html",cname,86400)
    except Exception:return []
    soup=BeautifulSoup(html,"html.parser")
    out=[]
    for table in soup.find_all("table"):
        head=_jra_text(table.find("thead") or table.find("tr"))
        if "年月日" not in head or "レース名" not in head: continue
        for tr in table.find_all("tr"):
            cells=tr.find_all(["th","td"])
            if len(cells)<8: continue
            vals=[_jra_text(c) for c in cells]
            dm=re.search(r"(20\d{2})年(\d{1,2})月(\d{1,2})日",vals[0])
            if not dm:continue
            iso=_jra_iso_date(int(dm.group(1)),int(dm.group(2)),int(dm.group(3)))
            if cutoff and iso>=cutoff:continue
            track=vals[1]
            title=vals[2]
            disttxt=vals[3]
            dsm=re.search(r"(芝|ダ|障)(\d{3,4})",disttxt)
            surface=dsm.group(1) if dsm else ""; dist=int(dsm.group(2)) if dsm else 0
            cond=vals[4] if len(vals)>4 else "不明"
            field=_int(vals[5]) if len(vals)>5 else 0
            finish=_int(vals[7]) if len(vals)>7 else 0
            jockey=vals[8] if len(vals)>8 else ""
            cw=float(re.sub(r"[^0-9.]","",vals[9]) or 0) if len(vals)>9 else 0
            tm=_jra_parse_time_seconds(vals[11] if len(vals)>11 else "")
            rc=_jra_attr_cname(tr,JRA_RESULT_CNAME_RE)
            rid=("jraresult-"+base64.urlsafe_b64encode(rc.encode()).decode().rstrip("=")) if rc else ""
            out.append({"date":iso,"track":track,"title":title,"distance":dist,"surface":surface,"condition":cond or "不明","weather":"不明","fieldSize":field,"finish":finish,"timeSeconds":tm,"cornerPositions":[],"carriedWeight":cw,"jockey":jockey,"raceId":rid,"source":"JRA公式競走馬情報"})
            if len(out)>=limit:return out
    return out
