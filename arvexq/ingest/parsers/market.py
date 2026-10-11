"""Extracted legacy behavior; network and stores stay outside this module."""
from __future__ import annotations

import json
import re
from bs4 import BeautifulSoup


def _parse_netkeiba_win_odds_payload(raw:str)->dict:
    if not raw:return {}
    s=str(raw).strip()
    if not s.startswith("{"):
        m=re.search(r"\((\{.*\})\)\s*;?\s*$",s,re.S)
        if m:s=m.group(1)
    try:body=json.loads(s)
    except Exception:return {}
    data=body.get("data") if isinstance(body,dict) else None
    odds=(data.get("odds") if isinstance(data,dict) else None) or {}
    win=odds.get("1") if isinstance(odds,dict) else None
    if win is None and isinstance(odds,dict):win=odds.get(1)
    if not isinstance(win,dict):return {}
    out={}
    for k,v in win.items():
        try:no=int(str(k))
        except Exception:continue
        odd=None;pop=None
        if isinstance(v,(list,tuple)):
            if len(v)>0:
                candidate=str(v[0]).replace(",","").strip()
                if re.fullmatch(r"\d+(?:\.\d+)?",candidate):
                    try:odd=float(candidate)
                    except Exception:odd=None
            if len(v)>2:
                try:pop=int(float(v[2]))
                except Exception:pop=None
        elif isinstance(v,dict):
            for kk in ("odds","win","tan"):
                if v.get(kk) not in (None,""):
                    try:odd=float(v.get(kk));break
                    except Exception:pass
            for kk in ("popularity","popular","rank","ninki"):
                if v.get(kk) not in (None,""):
                    try:pop=int(float(v.get(kk)));break
                    except Exception:pass
        if odd is not None and odd>0:
            out[no]={"winOdds":odd,"popularity":pop,"oddsSource":"netkeiba実オッズ"}
    return out


def _parse_payouts(soup) -> list[dict]:
    """Parse official payout tables robustly, including NAR line-break cells."""
    import unicodedata
    aliases={
        "単勝":"単勝","複勝":"複勝",
        "枠連":"枠連","枠複":"枠連","枠連複":"枠連",
        "馬連":"馬連","馬複":"馬連","馬連複":"馬連",
        "ワイド":"ワイド",
        "馬単":"馬単","馬連単":"馬単",
        "3連複":"3連複","三連複":"3連複","３連複":"3連複",
        "3連単":"3連単","三連単":"3連単","３連単":"3連単",
    }
    label_keys=sorted(aliases,key=len,reverse=True)
    out=[];seen=set()

    def norm(v):
        return re.sub(r"\s+","",unicodedata.normalize("NFKC",str(v or "")))

    def lines(cell):
        copy=BeautifulSoup(str(cell),"html.parser")
        for br in copy.find_all("br"):br.replace_with("\n")
        vals=[]
        for x in copy.get_text("\n").splitlines():
            x=norm(x)
            if x:vals.append(x)
        return vals

    def add(kind,combo,amount):
        kind=aliases.get(kind,kind);combo=norm(combo);amount=norm(amount)
        cm=re.fullmatch(r"\d+(?:[-→・]\d+){0,2}",combo)
        am=re.fullmatch(r"([\d,]+)円?",amount)
        if not cm or not am:return
        value=int(am.group(1).replace(",",""))
        key=(kind,combo,value)
        if key in seen:return
        seen.add(key)
        out.append({"type":kind,"combination":combo,"amount":value})

    for table in soup.find_all("table"):
        current=""
        for tr in table.find_all("tr"):
            cells=tr.find_all(["th","td"],recursive=False)
            if not cells:continue
            cell_lines=[lines(c) for c in cells]
            flat=[x for group in cell_lines for x in group]
            label_i=None;label_raw=""
            for i,group in enumerate(cell_lines):
                for v in group:
                    hit=next((k for k in label_keys if norm(v)==norm(k)),None)
                    if hit:
                        label_i=i;label_raw=hit;break
                if label_i is not None:break
            if label_i is not None:
                current=aliases[label_raw]
                payload=[x for group in cell_lines[label_i+1:] for x in group]
            elif current:
                payload=flat
            else:
                continue

            combos=[x for x in payload if re.fullmatch(r"\d+(?:[-→・]\d+){0,2}",norm(x))]
            amounts=[x for x in payload if re.fullmatch(r"[\d,]+円",norm(x))]
            if combos and amounts:
                for combo,amount in zip(combos,amounts):
                    add(current,combo,amount)

    if not out:
        raw=unicodedata.normalize("NFKC",soup.get_text("\n"))
        raw=re.sub(r"[ \t]+","",raw)
        labels="|".join(re.escape(k) for k in label_keys)
        chunks=list(re.finditer(rf"(?m)^({labels})\s*$",raw))
        for idx,m in enumerate(chunks):
            kind=aliases.get(norm(m.group(1)),norm(m.group(1)))
            seg=raw[m.end():chunks[idx+1].start() if idx+1<len(chunks) else m.end()+500]
            combos=re.findall(r"(?m)^(?:\s*)(\d+(?:[-→・]\d+){0,2})(?:\s*)$",seg)
            amounts=re.findall(r"([\d,]+)\s*円",seg)
            for combo,amount in zip(combos,amounts):
                add(kind,combo,amount+"円")
    return out

