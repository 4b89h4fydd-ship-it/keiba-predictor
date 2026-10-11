"""local/racecards: acquisition behavior preserved from PR #13 (95f2595).

Keyword-only ports are supplied by the application composition root.
This module never imports app or initializes storage/background workers.
"""
from arvexq.ingest.pure_parsers import _jra_decode
from arvexq.normalize.scalars import _clean
from arvexq.normalize.scalars import _scratch_status
from arvexq.normalize.scalars import _stable_id
from bs4 import BeautifulSoup
import json
import os
import re
import urllib.parse
import urllib.request


from arvexq.ingest.local.state import NAR_BABA_CODES

def nar_race_summaries(iso_date: str, *, DB_PATH, _new_conn) -> list[dict]:
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
                "horses":[],"result":{"status":"確定","finishers":[{"finish":1}]} if finalized else None,"source":"NAR公式"
            })
        return out
    finally:
        conn.close()


def nar_race_detail(race_id: str, *, NarStore) -> dict | None:
    m=re.match(r"^nar-(\d{4}-\d{2}-\d{2})-(.+)-(\d{2})$",race_id)
    if not m:return None
    iso_date,track,race_no=m.group(1),m.group(2),int(m.group(3))
    store=NarStore()
    try:
        race=store.conn.execute("SELECT * FROM races WHERE track=? AND date=? AND race_no=?",(track,iso_date,race_no)).fetchone()
        if not race:return None
        entries=store.conn.execute("SELECT * FROM entries WHERE track=? AND date=? AND race_no=? ORDER BY horse_no",(track,iso_date,race_no)).fetchall()
        horses=[]
        for e in entries:
            horses.append({
                "id":_stable_id(iso_date,track,race_no,e["horse_no"],e["name"]),"horseNumber":int(e["horse_no"]),
                "frameNumber":int(e["frame_no"] or 0),"name":e["name"],"age":int(e["age"] or 0),"sex":e["sex"] or "牡",
                "carriedWeight":float(e["carried_weight"] or 0),"jockey":e["jockey"] or "","trainer":e["trainer"] or "",
                "status":str(e["status"] or "") if "status" in e.keys() else "",
                "scratched":bool(_scratch_status(str(e["status"] or ""))) if "status" in e.keys() else False,
                "jockeyStats":store.stats("jockey",e["jockey"],iso_date),"trainerStats":store.stats("trainer",e["trainer"],iso_date),
                "jockeyProfile":store.role_profile("jockey",e["jockey"],iso_date,track,int(race["distance"] or 0),race["condition"] or "不明"),
                "trainerProfile":store.role_profile("trainer",e["trainer"],iso_date,track,int(race["distance"] or 0),race["condition"] or "不明"),
                "prizeMoneyAtRace":store.prize_before(e["name"],iso_date),"recentRaces":store.recent_races(e["name"],iso_date,5),
            })
        finishers=[]
        for e in entries:
            fin=int(e["finish"] or 0)
            if entries:
                try:cp=json.loads(e["corner_positions_json"] or "[]")
                except Exception:cp=[]
                finishers.append({"finish":fin,"horseNumber":int(e["horse_no"]),"frameNumber":int(e["frame_no"] or 0),"name":e["name"],"timeSeconds":float(e["time_seconds"] or 0),"cornerPositions":cp})
        finishers.sort(key=lambda x:(x["finish"] or 999,x["horseNumber"]))
        need=min(3,len(entries)); ranks={x["finish"] for x in finishers}; finalized=need>0 and all(i in ranks for i in range(1,need+1))
        detail={"id":race_id,"circuit":"地方","date":iso_date,"track":track,"raceNumber":race_no,
                "title":race["title"] or f"{race_no}R","distance":int(race["distance"] or 0),"condition":race["condition"] or "不明",
                "weather":race["weather"] or "不明","fieldSize":int(race["field_size"] or len(entries)),"racePrize1":int(race["prize1"] or 0),
                "surface":"","startTime":race["start_time"] or "","scheduledStartTime":race["scheduled_start_time"] or race["start_time"] or "",
                "startTimeChanged":bool((race["scheduled_start_time"] or "") and (race["start_time"] or "") and race["scheduled_start_time"]!=race["start_time"]),
                "horses":horses,"result":{"status":"確定","finishers":finishers} if finalized else None,"source":"NAR公式"}
        return detail
    finally:
        try:store.conn.close()
        except Exception:pass


def _parse_nar_official_card_html(detail: dict, html: str) -> list[dict]:
    """Parse the NAR official card including layouts where 馬体重 and 増減 are separate cells."""
    if not html:return []
    soup=BeautifulSoup(html,"html.parser")
    known={_clean(h.get("name")):int(h.get("horseNumber") or 0)
           for h in detail.get("horses",[]) or []
           if h.get("name") and int(h.get("horseNumber") or 0)>0}
    out_by_no={}

    def horse_no_from_row(tr, vals, rowtxt):
        for name,hno in known.items():
            if name and name in rowtxt:return hno
        # Prefer the explicit 馬番 area near the start of the row.
        nums=[]
        for c in vals[:8]:
            m=re.fullmatch(r"\D*(\d{1,2})\D*",c)
            if m:
                v=int(m.group(1))
                if 1<=v<=18:nums.append(v)
        return nums[-1] if nums else 0

    def parse_weight_cell(txt):
        m=re.search(r"(?<!\d)(\d{3})(?:\s*(?:kg)?)?(?:\s*[（(]\s*([+\-]?\d+)\s*[）)])?(?!\d)",txt,re.I)
        if not m:return None,None
        w=int(m.group(1))
        if not (250<=w<=800):return None,None
        c=int(m.group(2)) if m.group(2) is not None else None
        return w,c

    for table in soup.find_all("table"):
        rows=table.find_all("tr")
        if not rows:continue

        # Try the header-driven layout first. NAR often publishes 馬体重 and 変更
        # in separate columns, so the old "(+/-)"-only parser missed every horse.
        header_vals=[];header_idx=-1
        for ri,tr in enumerate(rows[:8]):
            vals=[_clean(c.get_text(" ",strip=True)) for c in tr.find_all(["th","td"],recursive=False)]
            compact=[re.sub(r"\s+","",x) for x in vals]
            if any("馬体重" in x for x in compact):
                header_vals=compact;header_idx=ri;break

        ibw=-1;ichg=-1;icw=-1
        if header_vals:
            for i,x in enumerate(header_vals):
                if ibw<0 and "馬体重" in x:ibw=i
                if ichg<0 and ("変更" in x or "増減" in x):ichg=i
                if icw<0 and ("負担重量" in x or "斤量" in x or x=="重量"):icw=i

        for tr in rows[(header_idx+1 if header_idx>=0 else 0):]:
            cells=tr.find_all(["th","td"],recursive=False)
            vals=[_clean(c.get_text(" ",strip=True)) for c in cells]
            rowtxt=_clean(tr.get_text(" ",strip=True))
            if not vals or not rowtxt:continue
            no=horse_no_from_row(tr,vals,rowtxt)
            if not no:continue

            weight=None;change=None;carried=None

            # Current carried weight is independent from body weight. Some NAR layouts
            # publish it as 負担重量 / 斤量, so fill a missing DB value from the card.
            if icw>=0 and icw<len(vals):
                cm=re.search(r"(?<!\d)(\d{2}(?:\.\d)?)(?!\d)",vals[icw])
                if cm:
                    try:
                        cv=float(cm.group(1))
                        if 35<=cv<=80:carried=round(cv,1)
                    except Exception:pass

            # 1) Exact body-weight column when the table aligns normally.
            if ibw>=0 and ibw<len(vals):
                weight,change=parse_weight_cell(vals[ibw])
                if weight and change is None and ichg>=0 and ichg<len(vals):
                    cm=re.search(r"([+\-]?\d{1,3})",vals[ichg])
                    if cm:
                        cv=int(cm.group(1))
                        if -99<=cv<=99:change=cv

            # 2) Layouts that render 482(+4) in one text block.
            if not weight:
                wm=re.search(r"(?<!\d)(\d{3})\s*(?:kg)?\s*[（(]\s*([+\-]?\d+)\s*[）)]",rowtxt,re.I)
                if wm:
                    w=int(wm.group(1))
                    if 250<=w<=800:
                        weight=w;change=int(wm.group(2))

            # 3) DebaTableSmall-style rows: current weight is a standalone 3-digit
            # cell and the change is the next small integer cell.
            if not weight:
                for i,cell in enumerate(vals[:24]):
                    if not re.fullmatch(r"\d{3}",cell):continue
                    w=int(cell)
                    if not (250<=w<=800):continue
                    weight=w
                    if i+1<len(vals):
                        cm=re.fullmatch(r"\s*([+\-]?\d{1,2})\s*",vals[i+1])
                        if cm:change=int(cm.group(1))
                    break

            if not weight and carried is None:continue
            out_by_no[no]={
                "horseNumber":no,
                "bodyWeight":weight,
                "bodyWeightChange":change,
                "carriedWeight":carried,
                "source":"NAR公式出馬表",
            }

    return [out_by_no[k] for k in sorted(out_by_no)]


def _nar_official_card_rows_fast(detail: dict, *, _parse_nar_official_card_html) -> list[dict]:
    """Fetch NAR official current body weight/change from multiple official card layouts."""
    code=NAR_BABA_CODES.get(str(detail.get("track") or ""))
    if not code:return []
    date=str(detail.get("date") or "")
    race_no=int(detail.get("raceNumber") or 0)
    if not date or not race_no:return []
    q=urllib.parse.urlencode({
        "k_babaCode":code,
        "k_raceDate":date.replace("-","/"),
        "k_raceNo":race_no,
    })
    # DebaTableSmall exposes 馬体重 / 変更 as simple columns and is the most
    # reliable source for the current value. Keep the other official layouts as fallbacks.
    urls=[
        "https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/DebaTableSmall?"+q,
        "https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/DebaTable?"+q,
        "https://www.keiba.go.jp/KeibaWeb_IPAT/TodayRaceInfo/DebaTable_ipat?"+q,
        "https://www.keiba.go.jp/KeibaWebSP/TodayRaceInfo/S_DebaTable?"+q,
        "https://sp.keiba.go.jp/KeibaWebSP/TodayRaceInfo/S_DebaTable?"+q,
    ]
    out_by_no={}
    # Every active runner matters. Do not stop at N-1 coverage: that caused the
    # last horse on some NAR cards to remain "未発表" even after the official
    # card had published its body weight.
    target=max(1,len([h for h in detail.get("horses",[]) or [] if not h.get("scratched")]))
    for url in urls:
        try:
            req=urllib.request.Request(url,headers={
                "User-Agent":"Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Safari/604.1",
                "Accept-Language":"ja-JP,ja;q=0.9",
                "Referer":"https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/TodayRaceInfoTop",
            })
            with urllib.request.urlopen(req,timeout=float(os.getenv("NAR_CARD_TIMEOUT_SEC","4.0"))) as res:
                html=_jra_decode(res.read())
        except Exception as exc:
            print("NAR official card failed",detail.get("id"),url,exc);continue
        for row in _parse_nar_official_card_html(detail,html):
            no=int(row.get("horseNumber") or 0)
            if no:out_by_no[no]=row
        if out_by_no and (not target or len(out_by_no)>=target):break
    return [out_by_no[k] for k in sorted(out_by_no)]
