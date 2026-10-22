"""Observed NAR official 単勝/複勝 odds parsing, separate from fetching and forecasting.

Moved verbatim from the production parser in app.py. The caller, input,
output fields, odds-rank ties and fallback behavior remain unchanged.
"""
import re

from bs4 import BeautifulSoup

from arvexq.ingest.field_normalization import _clean, _scratch_status
from arvexq.ingest.place_odds import place_odds_pair
from arvexq.ingest.odds_fields.nar_popularity import apply_observed_win_popularity


def _parse_nar_live_odds_html(html:str)->dict:
    """Parse NAR official 単・複 page across header and positional layouts."""
    if not html:return {}
    soup=BeautifulSoup(html,"html.parser")
    out={}

    # Header-driven layout.
    for table in soup.find_all("table"):
        rows=table.find_all("tr")
        if not rows:continue
        header=[];header_idx=-1
        for ri,tr in enumerate(rows[:4]):
            vals=[_clean(c.get_text(" ",strip=True)) for c in tr.find_all(["th","td"])]
            if any("馬番" in x for x in vals) and any("単勝" in x for x in vals):
                header=vals;header_idx=ri;break
        if not header:continue

        def idxpart(part):
            for i,x in enumerate(header):
                if part in x:return i
            return -1

        ino=idxpart("馬番");iodd=idxpart("単勝");ipop=idxpart("人気");ibw=idxpart("馬体重")
        for tr in rows[header_idx+1:]:
            vals=[_clean(c.get_text(" ",strip=True)) for c in tr.find_all(["th","td"])]
            if ino<0 or ino>=len(vals) or iodd<0 or iodd>=len(vals):continue
            mn=re.fullmatch(r"\D*(\d{1,2})\D*",vals[ino])
            if not mn:continue
            no=int(mn.group(1))
            om=re.search(r"(?<!\d)(\d+(?:\.\d+)?)(?!\d)",vals[iodd])
            odds=float(om.group(1)) if om else 0.0
            scratch_status=_scratch_status(vals[iodd])
            pop=0
            if ipop>=0 and ipop<len(vals):
                pm=re.search(r"\d+",vals[ipop]);pop=int(pm.group()) if pm else 0
            bw=0;chg=None
            if ibw>=0 and ibw<len(vals):
                bm=re.search(r"(\d{3})(?:\s*[（(]\s*([+\-]?\d+)\s*[）)])?",vals[ibw])
                if bm:
                    bw=int(bm.group(1));chg=int(bm.group(2)) if bm.group(2) is not None else None
            if odds<=0 and not bw and not scratch_status:
                continue
            out[no]={"winOdds":odds or None,"popularity":pop or None,"bodyWeight":bw or None,
                     "bodyWeightChange":chg,"oddsSource":"NAR公式" if odds else "NAR公式出馬表",
                     "status":scratch_status,"scratched":bool(scratch_status)}

    # Current official layout second pass:
    # 枠 | 馬番 | 馬名 | 単勝 | 複勝下限 | 複勝上限 | 性齢 | 馬体重 ...
    # Always run this pass, even when the header-driven pass already found odds.
    # NAR uses multi-row/rowspan headers and the header index can be shifted for
    # 馬体重 on only one runner. Previously `if not out` skipped this reliable
    # flat-row pass as soon as odds existed, leaving cases such as the last horse
    # with odds but bodyWeight=None. Merge the flat row into missing live fields.
    for table in soup.find_all("table"):
        for tr in table.find_all("tr"):
            vals=[_clean(c.get_text(" ",strip=True)) for c in tr.find_all(["th","td"])]
            if len(vals)<4:continue
            m0=re.fullmatch(r"\d{1,2}",vals[0])
            m1=re.fullmatch(r"\d{1,2}",vals[1]) if len(vals)>1 else None
            oddm=re.fullmatch(r"\d+(?:\.\d+)?",vals[3]) if len(vals)>3 else None
            scratch_status=_scratch_status(vals[3] if len(vals)>3 else "")
            if not (m0 and m1 and (oddm or scratch_status)):continue
            no=int(m1.group());odds=float(oddm.group()) if oddm else 0.0
            if no<=0 or (odds<=0 and not scratch_status):continue
            bw=0;chg=None
            for cell in vals[6:10]:
                bm=re.search(r"(\d{3})\s*(?:[（(]\s*([+\-]?\d+)\s*[）)])?",cell)
                if bm:
                    bw=int(bm.group(1));chg=int(bm.group(2)) if bm.group(2) is not None else None
                    break
            z=out.setdefault(no,{})
            # Separate official 複勝 odds columns. No imputation from 単勝.
            if len(vals)>5:
                observed_place=place_odds_pair(vals[4],vals[5])
                if observed_place:z.update(observed_place)
            if odds>0:z["winOdds"]=odds
            if bw:
                z["bodyWeight"]=bw
                z["bodyWeightChange"]=chg
            z["oddsSource"]="NAR公式" if odds else z.get("oddsSource","")
            if scratch_status:
                z["status"]=scratch_status;z["scratched"]=True
            else:
                z.setdefault("status","");z.setdefault("scratched",False)

    return apply_observed_win_popularity(out)
