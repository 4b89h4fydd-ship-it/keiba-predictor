"""Extracted legacy behavior; network and stores stay outside this module."""
from __future__ import annotations

from arvexq.prediction.pure_diagnostics import _pc_time_index, _pc_season


def _pc_clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, float(v)))


def _pc_race_field(rr: dict) -> int:
    return max(4, int(rr.get("fieldSize") or 12))


def _pc_finish_quality(rr: dict) -> float:
    fin=int(rr.get("finish") or 0); fs=_pc_race_field(rr)
    if fin <= 0:return .45
    return _pc_clamp(1-(fin-1)/max(3,fs-1))


def _pc_list_quality(rows: list[dict], target_dist: int) -> float:
    if not rows:return .5
    num=den=0.0
    for i,rr in enumerate(rows):
        w=.82**i
        q=_pc_finish_quality(rr)
        ti=_pc_time_index(rr,target_dist)
        q=q*.72+(_pc_clamp(ti/18) if ti else .5)*.28
        num+=q*w;den+=w
    return num/den if den else .5


def _pc_style_metrics(horse: dict, race: dict) -> dict:
    rs=list(horse.get("recentRaces") or [])
    c=[0.0,0.0,0.0,0.0];den=early_den=early3=moved3=tempo_num=tempo_den=0.0;samples=0
    target=int(race.get("distance") or 0)
    for i,rr in enumerate(rs):
        pos_list=list(rr.get("cornerPositions") or [])
        try:pos=int(pos_list[0]) if pos_list else 0
        except Exception:pos=0
        if pos <= 0:continue
        fs=_pc_race_field(rr); norm=(pos-1)/max(1,fs-1)
        delta=abs(int(rr.get("distance") or 0)-target)
        rel=1.22 if delta<=100 else (1.08 if delta<=300 else (.74 if delta>=700 else 1.0))
        if str(rr.get("track") or "")==str(race.get("track") or ""):rel*=1.10
        if str(rr.get("condition") or "") not in ("","不明") and str(rr.get("condition") or "")==str(race.get("condition") or ""):rel*=1.05
        w=(.82**i)*rel;den+=w;early_den+=w;samples+=1
        if pos==1:c[0]+=w
        elif pos<=3 or norm<=.22:c[1]+=w
        elif norm<=.62:c[2]+=w
        else:c[3]+=w
        if pos<=3:early3+=w
        later=[]
        for z in pos_list[1:]:
            try:
                z=int(z)
                if z>0:later.append(z)
            except Exception:pass
        if pos>3 and later and min(later)<=3:moved3+=w
        ten=_pc_clamp(1-(pos-1)/max(3,fs-1));tempo_num+=ten*w;tempo_den+=w
    if not den:
        return {"front":0,"stalk":0,"mid":0,"close":0,"early3":0,"moved3":0,"ten":.5,"samples":0,"stylePoint":None,"pastStyle":"履歴なし"}
    front,stalk,mid,close=[z/den for z in c]
    point=front+2*stalk+3*mid+4*close
    name="逃げ" if point<1.65 else ("先行" if point<2.35 else ("差し" if point<3.15 else "追込"))
    return {"front":front,"stalk":stalk,"mid":mid,"close":close,"early3":early3/early_den if early_den else 0,"moved3":moved3/early_den if early_den else 0,"ten":tempo_num/tempo_den if tempo_den else .5,"samples":samples,"stylePoint":round(point,4),"pastStyle":name}


def _pc_sectional_score(horse: dict, race: dict) -> tuple[float | None, int]:
    """Closing-section evidence from historical 3F times, normalized by each run's own average speed.

    This deliberately uses only past-race data. It does not infer missing sectionals and
    never reads the current race result/market. The ratio makes the signal portable across
    distances/tracks better than comparing raw 3F seconds directly.
    """
    rows=list(horse.get("allPastRuns") or horse.get("recentRaces") or [])
    target=int(race.get("distance") or 0); num=den=0.0; used=0
    for i,rr in enumerate(rows[:8]):
        try:
            ag=float(rr.get("agari3f") or rr.get("agari") or 0)
            sec=float(rr.get("timeSeconds") or 0)
            dist=int(rr.get("distance") or 0)
        except Exception:
            continue
        if not (27.0 <= ag <= 50.0) or sec <= 0 or dist < 600:
            continue
        avg_speed=dist/sec
        close_speed=600.0/ag
        if avg_speed <= 0:continue
        ratio=close_speed/avg_speed
        # Around 1.00 is an even finish; 1.15-1.30 is a strong closing section.
        q=_pc_clamp((ratio-.96)/.36)
        try:rank=int(rr.get("agariRank") or rr.get("agari_rank") or 0)
        except Exception:rank=0
        if rank>0:
            fs=_pc_race_field(rr)
            rq=_pc_clamp(1-(rank-1)/max(3,fs-1))
            q=q*.82+rq*.18
        delta=abs(dist-target) if target else 0
        rel=1.16 if delta<=100 else (1.06 if delta<=300 else (.78 if delta>=700 else .94))
        if str(rr.get("track") or "")==str(race.get("track") or ""):rel*=1.06
        w=(.84**i)*rel
        num+=q*w;den+=w;used+=1
    return ((num/den) if den else None),used


def _pc_fit_metrics(horse: dict, race: dict) -> dict:
    rs=list(horse.get("recentRaces") or []); target=int(race.get("distance") or 0); target_season=_pc_season(str(race.get("date") or ""))
    groups={"track":[],"distance":[],"condition":[],"weather":[],"season":[],"level":[]}
    for rr in rs:
        dist=int(rr.get("distance") or 0);delta=abs(dist-target)
        if str(rr.get("track") or "")==str(race.get("track") or ""):groups["track"].append(rr)
        if delta<=100 or (target>=1800 and delta<=200):groups["distance"].append(rr)
        if str(rr.get("condition") or "") not in ("","不明") and str(rr.get("condition") or "")==str(race.get("condition") or ""):groups["condition"].append(rr)
        if str(rr.get("weather") or "") not in ("","不明") and str(rr.get("weather") or "")==str(race.get("weather") or ""):groups["weather"].append(rr)
        if _pc_season(str(rr.get("date") or ""))==target_season:groups["season"].append(rr)
        rp=int(rr.get("racePrize1") or 0);tp=int(race.get("racePrize1") or 0)
        if tp>0 and rp>=tp*.8:groups["level"].append(rr)
    out={k:_pc_list_quality(v,target) for k,v in groups.items()}
    out["counts"]={k:len(v) for k,v in groups.items()}
    return out

