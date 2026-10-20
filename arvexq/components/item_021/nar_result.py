"""NAR official result HTML parsing; caller owns source selection and I/O."""
import re
import unicodedata
from bs4 import BeautifulSoup
from arvexq.ingest.result_status.confirmed import official_confirmed


def parse_result_html(html: str, *, known, clean, parse_payouts, clean_weather, clean_condition):
    soup=BeautifulSoup(html,"html.parser")
    full=clean(soup.get_text(" ",strip=True))
    if "競走成績" not in full and "着順" not in full:return None
    wm=re.search(r"天候\s*[：:]?\s*(小雨|小雪|晴|曇|雨|雪)",full)
    cm=re.search(r"馬場(?:状態)?\s*[：:]?\s*(不良|稍重|重|良)",full)
    finishers=[]
    for table in soup.find_all("table"):
        rows=table.find_all("tr")
        if not rows:continue
        headers=[];header_i=-1
        for ri,tr in enumerate(rows[:4]):
            vals=[clean(c.get_text(" ",strip=True)) for c in tr.find_all(["th","td"],recursive=False)]
            joined="|".join(vals)
            if "着順" in joined and "馬体重" in joined and "馬番" in joined:
                headers=vals;header_i=ri;break
        if not headers:continue
        def hi(part):
            for i,x in enumerate(headers):
                if part in x:return i
            return -1
        idx={k:hi(v) for k,v in {
            "fin":"着順","frame":"枠","no":"馬番","name":"馬名","sexage":"性齢",
            "cw":"負担","jockey":"騎手","trainer":"調教師","bw":"馬体重",
            "time":"タイム","corner":"コーナー","pop":"人気","odds":"単勝","margin":"着差"
        }.items()}
        for tr in rows[header_i+1:]:
            cells=tr.find_all(["th","td"],recursive=False)
            vals=[clean(c.get_text(" ",strip=True)) for c in cells]
            if not vals:continue
            def val(key):
                j=idx.get(key,-1)
                return vals[j] if j>=0 and j<len(vals) else ""
            fin_txt=val("fin") or vals[0]
            mf=re.match(r"^\s*(\d+)\s*$",fin_txt)
            if not mf:continue
            fin=int(mf.group(1))
            name=val("name")
            no=0
            mno=re.search(r"\d+",val("no")) if val("no") else None
            if mno:no=int(mno.group())
            if not no and name:no=known.get(clean(name),0)
            if not no:
                for nm,hno in known.items():
                    if nm and nm in clean(tr.get_text(" ",strip=True)):
                        no=hno;name=name or nm;break
            if not no:continue
            fr=0;mfr=re.search(r"\d+",val("frame")) if val("frame") else None
            if mfr:fr=int(mfr.group())
            bw=None;chg=None
            bwtxt=val("bw") or clean(tr.get_text(" ",strip=True))
            mbw=re.search(r"(?<!\d)(\d{3,4})\s*(?:kg)?\s*[（(]\s*([+\-]?\d+)\s*[）)]",bwtxt)
            if mbw:bw=int(mbw.group(1));chg=int(mbw.group(2))
            tm=0.0;mt=re.search(r"(\d+):(\d{1,2}(?:\.\d+)?)",unicodedata.normalize("NFKC",val("time")))
            if mt:tm=int(mt.group(1))*60+float(mt.group(2))
            corners=[]
            ctext=val("corner")
            mcorn=re.search(r"(?<!\d)(\d{1,2}(?:-\d{1,2}){1,4})(?!\d)",ctext)
            if mcorn:
                try:corners=[int(x) for x in mcorn.group(1).split("-")]
                except Exception:corners=[]
            pop=None;mp=re.search(r"\d+",val("pop")) if val("pop") else None
            if mp:pop=int(mp.group())
            odd=None;mo=re.search(r"\d+(?:\.\d+)?",val("odds")) if val("odds") else None
            if mo:
                try:odd=float(mo.group())
                except Exception:odd=None
            # Official NAR result tables do not always publish a 3F split.
            # Missing values are unknown, never inherited from another finisher.
            last3f=None
            last3f_idx=hi("上り") if hi("上り")>=0 else hi("上がり")
            if last3f_idx>=0 and last3f_idx<len(vals):
                token=re.search(r"\d{2}(?:\.\d)?",vals[last3f_idx])
                if token:
                    try:last3f=float(token.group())
                    except (TypeError,ValueError):last3f=None
            margin_text=val("margin")
            if not margin_text and idx.get("margin",-1)<0:
                t_idx=idx.get("time",-1)
                if t_idx>=0 and t_idx+1<len(vals):
                    candidate=unicodedata.normalize("NFKC",vals[t_idx+1]).strip()
                    if re.fullmatch(r"(?:クビ|ハナ|アタマ|大差|同着|[0-9]+(?:[/][0-9]+)?)",candidate):
                        margin_text=candidate
            finishers.append({
                "finish":fin,"finishLabel":f"{fin}着","horseNumber":no,
                "frameNumber":fr or int((no+1)//2),"name":name or next((nm for nm,hno in known.items() if hno==no),""),
                "timeSeconds":tm,"last3FSeconds":last3f,"cornerPositions":corners,"bodyWeight":bw,"bodyWeightChange":chg,
                "popularity":pop,"winOdds":odd,
            })
        if finishers:break
    finishers.sort(key=lambda x:(int(x.get("finish") or 999),int(x.get("horseNumber") or 999)))
    # Do not call a partial page final until at least the podium is visible.
    classified=[int(x.get("finish") or 0) for x in finishers if int(x.get("finish") or 0)>0]
    if 1 not in classified or sum(1 for finish in classified if finish<=3)<3:return None
    payouts=parse_payouts(soup)
    explicit_final=official_confirmed(full)
    out={"status":"確定" if explicit_final else "速報","finishers":finishers,"source":"NAR公式競走成績","payouts":payouts}
    if wm:out["weather"]=clean_weather(wm.group(1))
    if cm:out["condition"]=clean_condition(cm.group(1))
    return out
