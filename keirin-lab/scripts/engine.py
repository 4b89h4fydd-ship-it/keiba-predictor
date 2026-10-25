"""Keirin lineup and track heuristic. Coefficients provisional, not calibrated."""
import math,re
TRACKS={"川崎":(400,58.0),"青森":(400,58.9),"名古屋":(400,58.8),"防府":(333,42.5),"奈良":(333,38.0),"小松島":(400,55.5),"京王閣":(400,51.5),"小田原":(333,36.1),"和歌山":(400,59.9),"熊本":(400,60.3),"小倉":(400,56.9),"高知":(500,52.0),"松戸":(333,38.2),"前橋":(335,46.7),"宇都宮":(500,63.3),"大宮":(500,66.7)}
def predict(race):
    raw=race.get("entries") or []
    if not 3<=len(raw)<=9:return None
    try:
        riders=[dict(n=int(x["umaban"]),name=x.get("name",""),score=float(x["score"]),win=float(x["win_rate"])/100,place=float(x["top3_rate"])/100,style=x.get("style",""),comment=x.get("comment","")) for x in raw]
    except (ValueError,TypeError,KeyError):return None
    if len({x["n"] for x in riders})!=len(riders) or any(not(0<=x["win"]<=x["place"]<=1) for x in riders):return None
    parent={r["n"]:None for r in riders}
    for r in riders:
        c=re.sub(r"\s+","",r["comment"])
        for t in riders:
            if t["n"]==r["n"]:continue
            name=re.sub(r"\s+","",t["name"])
            if len(name)>=2 and any(word in c for word in (name+"君",name+"さん",name+"へ",name[:2]+"君",name[:2]+"さん")):
                parent[r["n"]]=t["n"];break
    def root(n):
        seen=set()
        while parent.get(n) is not None and n not in seen:
            seen.add(n);n=parent[n]
        return n
    groups={}
    for r in riders:groups.setdefault(root(r["n"]),[]).append(r["n"])
    lines=list(groups.values())
    length,straight=TRACKS.get(race.get("venue"),(400,55.0))
    leader={x[0] for x in lines}
    leadcount=sum(x["n"] in leader and x["style"]=="逃" for x in riders)
    avg=sum(x["score"] for x in riders)/len(riders)
    for r in riders:
        group=next(x for x in lines if r["n"] in x)
        pos=group.index(r["n"])
        track=(.14 if length==333 else -.06 if length==500 else .05) if r["style"]=="逃" else 0
        track+=(.10 if straight>=57 else -.05 if straight<45 else 0) if r["style"]=="追" else 0
        line=(.09 if pos==0 else .12 if pos==1 else .02) if len(group)>1 else 0
        pace=(.13 if r["style"]=="追" else -.17 if r["style"]=="逃" else .05) if leadcount>=3 else (.12 if leadcount<=1 and r["style"]=="逃" else 0)
        z=(r["score"]-avg)/8+1.1*(r["win"]-.15)+.5*(r["place"]-.4)+(.08 if r["style"]=="逃" else 0)+track+line+pace
        r["weight"]=math.exp(max(-8,min(8,z)))
        r["group"]=group
    total=sum(x["weight"] for x in riders);out=[]
    for a in riders:
        for b in riders:
            for c in riders:
                if len({a["n"],b["n"],c["n"]})<3:continue
                p=a["weight"]/total*b["weight"]/(total-a["weight"])*c["weight"]/(total-a["weight"]-b["weight"])
                if a["group"] is b["group"] and len(a["group"])>1:p*=1.12
                if b["group"] is c["group"] and len(b["group"])>1:p*=1.08
                out.append({"ticket":f'{a["n"]}-{b["n"]}-{c["n"]}',"p":p})
    norm=sum(x["p"] for x in out)
    for x in out:x["p"]/=norm
    out.sort(key=lambda x:-x["p"])
    probs={r["n"]:{"number":r["n"],"p1":0,"p3":0} for r in riders}
    for x in out:
        a,b,c=map(int,x["ticket"].split("-"))
        probs[a]["p1"]+=x["p"]
        for n in (a,b,c):probs[n]["p3"]+=x["p"]
    ranked=sorted(probs.values(),key=lambda x:-x["p1"])
    marks=dict(zip(("◎","○","▲","△","☆"),(r["number"] for r in ranked[:5])))
    scenario="先行型複数・踏み合いに注意" if leadcount>=3 else "先行ライン主導に注意" if leadcount==1 else "主導権不明確・自在戦を想定"
    return {"model":"keirin-line-track-v2-heuristic-uncalibrated","marks":marks,"riders":ranked,"trifecta":out[:20],"lines":lines,"scenario":scenario,"track":{"length":length,"straight":straight},"line_inference":"Unverified comments-derived groups","calibrated":False}
