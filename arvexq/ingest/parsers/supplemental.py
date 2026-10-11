"""Extracted legacy behavior; network and stores stay outside this module."""
from __future__ import annotations

import re
from arvexq.ingest.pure_parsers import _pick
from arvexq.normalize.scalars import _clean


def _parse_recent_cell(txt:str)->dict|None:
    s=_clean(txt)
    md=re.search(r"(20\d{2})[./](\d{1,2})[./](\d{1,2})\s*([^\s]+)\s+(\d+)\s+(.+?)\s+((?:芝|ダ|障)[^0-9 ]*)(\d{3,4})",s)
    if not md:return None
    date=f"{int(md.group(1)):04d}-{int(md.group(2)):02d}-{int(md.group(3)):02d}";track=md.group(4);finish=int(md.group(5));title=_clean(md.group(6));distance=int(md.group(8));surface=md.group(7)
    tm=0.0;mt=re.search(r"\b(\d+):(\d{2}\.\d)\b",s)
    if mt:tm=int(mt.group(1))*60+float(mt.group(2))
    cond="不明";mc=re.search(r"(?:^|\s)(良|稍|重|不)(?:\s|$)",s)
    if mc:cond=mc.group(1)
    field=0;mf=re.search(r"(\d+)頭",s);field=int(mf.group(1)) if mf else 0
    corners=[]
    for cm in re.findall(r"(?<!\d)(\d{1,2}(?:-\d{1,2}){1,3})(?!\d)",s):
        vals=[int(x) for x in cm.split("-")]
        if vals and max(vals)<=(field if field else 30):
            corners=vals;break
    # 斤量は「通過順」の直前にある。単純に最初の2桁を拾うと着順(10〜18)や
    # 頭数を誤って斤量にしてしまうため、通過順の直前を優先して探す。
    cw=0.0;mw=re.search(r"(?<!\d)(\d{2}(?:\.\d)?)\s+(?=\d{1,2}(?:-\d{1,2}){1,3}(?!\d))",s)
    if not mw:mw=re.search(r"(?<!\d)(5[0-9](?:\.\d)?)(?!\d)",s)
    if not mw:mw=re.search(r"\s(\d{2}(?:\.\d)?)\s",s)
    if mw:
        try:cw=float(mw.group(1))
        except Exception:pass
    return {"date":date,"track":track,"title":title,"distance":distance,"surface":"障害" if surface.startswith("障") else ("芝" if surface.startswith("芝") else "ダート"),"condition":cond,"weather":"不明","fieldSize":field,"finish":finish,"timeSeconds":tm,"cornerPositions":corners,"carriedWeight":cw,"source":"netkeiba"}


def _safe_float(v):
    try:
        if v is None or v=="": return None
        if isinstance(v,str):
            m=re.search(r"-?\d+(?:\.\d+)?",v.replace(",","").strip())
            if not m:return None
            v=m.group(0)
        return float(v)
    except Exception:return None


def _safe_int(v):
    x=_safe_float(v); return int(x) if x is not None else None


def _smart_normalize_row(x:dict)->dict|None:
    if not isinstance(x,dict):return None
    no=_safe_int(_pick(x,"horseNumber","horse_no","uno","number","馬番")); name=str(_pick(x,"name","hname","horseName","馬名") or "").strip()
    if not no and not name:return None
    smart={"ten1f":_pick(x,"ten1f","ten1f_best","h1_ten1f","テン1F"),"ten":_pick(x,"ten","ten_pat","ten_has","テン"),"agari":_pick(x,"agari","agari3f","furlong3","agari_pat","agari_has","上がり"),"estimatedPopularity":_pick(x,"estimatedPopularity","est_pop","推人","推定人気")}
    out={"horseNumber":no,"name":name,"smartRc":smart}
    rr=_pick(x,"recentRaces","recent_races")
    if isinstance(rr,list):out["recentRaces"]=[z for z in rr if isinstance(z,dict)][:5]
    return out

