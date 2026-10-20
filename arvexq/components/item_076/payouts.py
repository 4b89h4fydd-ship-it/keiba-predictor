"""Observed provider payout table parsing, independent of acquisition and forecasts."""
import re
from bs4 import BeautifulSoup

def parse_payouts(soup) -> list[dict]:
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
