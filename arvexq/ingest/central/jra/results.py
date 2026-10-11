"""central/jra/results: acquisition behavior preserved from PR #13 (95f2595).

Keyword-only ports are supplied by the application composition root.
This module never imports app or initializes storage/background workers.
"""
from arvexq.ingest.parsers.market import _parse_payouts
from arvexq.normalize.scalars import _clean
from bs4 import BeautifulSoup
import re


from arvexq.ingest.central.jra.state import JRA_BAD_TITLE_RE

def _jra_parse_result(result_cname: str, base: dict | None=None, *, _jra_any_race_no, _jra_any_track, _jra_date_from_cname, _jra_parse_time_seconds, _jra_request, _jra_text) -> dict | None:
    if not result_cname:return None
    try:html=_jra_request("https://www.jra.go.jp/JRADB/accessS.html",result_cname,20)
    except Exception as exc:
        print("JRA official result fetch failed",result_cname,exc);return None
    soup=BeautifulSoup(html,"html.parser");full=_jra_text(soup)
    date=_jra_date_from_cname(result_cname) or str((base or {}).get("date") or "")
    track=_jra_any_track(result_cname) or str((base or {}).get("track") or "")
    race_no=_jra_any_race_no(result_cname) or int((base or {}).get("raceNumber") or 0)
    sm=re.search(r"発走時刻\s*[：:]?\s*(\d{1,2})時\s*(\d{2})分",full)
    start=f"{int(sm.group(1)):02d}:{sm.group(2)}" if sm else str((base or {}).get("startTime") or "")
    dm=re.search(r"コース\s*[：:]?\s*([\d,]+)\s*メートル\s*[（(]([^）)]+)[）)]",full)
    distance=int(dm.group(1).replace(",","")) if dm else int((base or {}).get("distance") or 0)
    desc=dm.group(2) if dm else str((base or {}).get("surface") or "")
    surface="障害" if "障" in desc else ("芝" if "芝" in desc else ("ダート" if "ダ" in desc else str((base or {}).get("surface") or "")))
    weather="不明";wm=re.search(r"天候\s*[：:]?\s*(晴|曇|雨|小雨|雪|小雪)",full)
    if wm:weather=wm.group(1)
    conds=[]
    for typ in ("芝","ダート"):
        cm=re.search(typ+r"\s*[：:]?\s*(良|稍重|重|不良)",full)
        if cm:conds.append((typ,cm.group(1)))
    condition="不明"
    if surface=="芝":condition=next((c for t,c in conds if t=="芝"),condition)
    elif surface=="ダート":condition=next((c for t,c in conds if t=="ダート"),condition)
    elif conds:condition=conds[-1][1]
    title=""
    for node in soup.find_all(["h2","h3"]):
        tx=_jra_text(node)
        if tx and len(tx)<100 and not JRA_BAD_TITLE_RE.search(tx) and "レース結果" not in tx and not re.match(r"^\d+レース$",tx):title=tx;break
    if not title:title=str((base or {}).get("title") or f"{race_no}R")
    table=None;headers=[]
    for tb in soup.find_all("table"):
        for tr in tb.find_all("tr")[:5]:
            vals=[re.sub(r"\s+","",_jra_text(c)) for c in tr.find_all(["th","td"])]
            if any("着順" in v for v in vals) and any("馬番" in v for v in vals) and any("馬名" in v for v in vals):table=tb;headers=vals;break
        if table:break
    if table is None:return None
    def hidx(*keys):
        for i,v in enumerate(headers):
            for k in keys:
                if k in v:return i
        return -1
    ix={"fin":hidx("着順"),"frame":hidx("枠"),"no":hidx("馬番"),"name":hidx("馬名"),"sexage":hidx("性齢"),"cw":hidx("負担重量","斤量"),"jockey":hidx("騎手名","騎手"),"time":hidx("タイム"),"last3f":hidx("推定上り","上り"),"corner":hidx("コーナー通過順位","コーナー通過順"),"bw":hidx("馬体重"),"trainer":hidx("調教師名","調教師"),"pop":hidx("単勝人気","人気")}
    finishers=[]
    for tr in table.find_all("tr"):
        tds=tr.find_all("td")
        if not tds:continue
        vals=[_jra_text(td) for td in tds]
        def val(k):
            i=ix[k];return vals[i] if 0<=i<len(vals) else ""
        fm=re.search(r"\d+",val("fin"));nm=re.search(r"\d+",val("no"))
        if not nm:continue
        fin=int(fm.group()) if fm else 0;no=int(nm.group());mf=re.search(r"\d+",val("frame"));frame=int(mf.group()) if mf else 0
        name=_clean(val("name"));sxage=val("sexage");sx="";age=0;smx=re.search(r"(牡|牝|せん)(\d+)",sxage)
        if smx:sx=smx.group(1);age=int(smx.group(2))
        mcw=re.search(r"\d+(?:\.\d+)?",val("cw"));cw=float(mcw.group()) if mcw else 0.0
        tm=_jra_parse_time_seconds(val("time"));m3=re.search(r"\d+(?:\.\d+)?",val("last3f"));last3f=float(m3.group()) if m3 else None;corners=[];cm=re.search(r"\d{1,2}(?:-\d{1,2})+",val("corner"))
        if cm:corners=[int(x) for x in cm.group().split("-")]
        elif val("corner"):corners=[int(x) for x in re.findall(r"\d{1,2}",val("corner"))]
        bw=None;chg=None;mb=re.search(r"(\d{3})(?:\s*[（(]\s*([+\-]?\d+)\s*[）)])?",val("bw"))
        if mb:bw=int(mb.group(1));chg=int(mb.group(2)) if mb.group(2) is not None else None
        mp=re.search(r"\d+",val("pop"));pop=int(mp.group()) if mp else None
        finishers.append({"finish":fin,"finishLabel":str(fin)+"着" if fin else val("fin"),"horseNumber":no,"frameNumber":frame,"name":name,"sex":sx,"age":age,"carriedWeight":cw,"jockey":_clean(val("jockey")),"trainer":_clean(val("trainer")),"timeSeconds":tm,"last3FSeconds":last3f,"cornerPositions":corners,"bodyWeight":bw,"bodyWeightChange":chg,"popularity":pop})
    sectionals=sorted({float(x.get("last3FSeconds")) for x in finishers if x.get("last3FSeconds") not in (None,"") and float(x.get("last3FSeconds"))>0})
    for x in finishers:
        try:s=float(x.get("last3FSeconds")) if x.get("last3FSeconds") not in (None,"") else 0.0
        except (TypeError,ValueError):s=0.0
        if s>0 and sectionals:
            rk=sectionals.index(s)+1
            x["last3FRank"]=rk
            x["last3FPercentile"]=0.5 if len(sectionals)==1 else 1.0-(rk-1)/(len(sectionals)-1)
    finishers.sort(key=lambda x:(int(x.get("finish") or 999),int(x.get("horseNumber") or 999)))
    if not finishers:return None
    payouts=_parse_payouts(soup)
    status="確定" if payouts or re.search(r"確定",full) else "速報"
    prize1=0
    pm=re.search(r"1着\s*([\d,.]+)",full)
    if pm:
        try:prize1=int(float(pm.group(1).replace(",",""))*10000)
        except (TypeError,ValueError):prize1=0
    return {"date":date,"track":track,"raceNumber":race_no,"title":title,"distance":distance,"surface":surface,"condition":condition,"weather":weather,"fieldSize":len(finishers),"racePrize1":prize1,"startTime":start,"scheduledStartTime":start,"result":{"status":status,"finishers":finishers,"source":"JRA公式","payouts":payouts},"resultCname":result_cname,"source":"JRA公式結果"}
