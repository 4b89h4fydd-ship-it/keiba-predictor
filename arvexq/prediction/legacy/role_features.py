"""Legacy calculations with explicit dependencies; formulas preserved."""
from __future__ import annotations

import math
from arvexq.prediction.legacy.common import _v207_norm01, _v213_rank_percentiles


def _saved_role_scores(horse: dict) -> tuple[float,float,float]:
    """Stable pre-race P1/P2/P3 scores stored with the snapshot.

    These are intentionally market-blind. P1 emphasizes repeatable winning evidence;
    P2 emphasizes stability/front-hold; P3 allows peak/late-role evidence to surface.
    """
    e=horse.get('integratedEvaluation') or {}
    c=e.get('components') or {}
    pm=horse.get('precomputedMetrics') or {}
    fit=pm.get('fit') or {}
    st=pm.get('style') or {}
    def u(v,default=.5):
        try:
            x=float(v)
            return max(0.0,min(1.0,x)) if math.isfinite(x) else default
        except (TypeError,ValueError):
            return default
    base=u(float(e.get('score') or 50)/100)
    perf=u(c.get('racePerformance'))
    rep=u(c.get('representative'))
    track=u(fit.get('track'))
    dist=u(fit.get('distance'))
    going=u(fit.get('condition'))
    level=u(fit.get('level'))
    jockey=u(c.get('jockeyScore',c.get('jockeyResults')))
    body=u(c.get('bodyWeightScore'))
    lap=u(c.get('lapScore'))
    ten=u(st.get('ten'))
    early3=u(st.get('early3'))
    moved3=u(st.get('moved3'))
    front=u(st.get('front'))
    stalk=u(st.get('stalk'))
    mid=u(st.get('mid'))
    close=u(st.get('close'))
    samples=max(0,int(st.get('samples') or 0))
    evidence=min(1.0,samples/5.0)
    p1=(base*.26+perf*.20+rep*.15+dist*.10+track*.09+level*.07+going*.04+
        jockey*.025+body*.015+lap*.02+ten*.02+evidence*.01)
    p2=(base*.18+perf*.19+dist*.08+track*.08+going*.05+early3*.12+stalk*.08+
        front*.05+ten*.06+jockey*.025+evidence*.055)
    p3=(base*.14+perf*.14+rep*.14+dist*.06+track*.05+level*.05+going*.04+
        moved3*.10+mid*.07+close*.08+lap*.06+evidence*.07)
    return tuple(round(max(0.0,min(1.0,z))*100,2) for z in (p1,p2,p3))


def _v213_feature_rows(detail: dict, horses: list[dict]) -> list[dict[str,float]]:
    rows=[];field=max(1,len(horses))
    weights=[];ages=[]
    for h in horses:
        try:w=float(h.get('carriedWeight'));weights.append(w if math.isfinite(w) else None)
        except (TypeError,ValueError):weights.append(None)
        try:a=float(h.get('age'));ages.append(a if math.isfinite(a) else None)
        except (TypeError,ValueError):ages.append(None)
    wv=[x for x in weights if x is not None];av=[x for x in ages if x is not None]
    wmin,wmax=(min(wv),max(wv)) if wv else (0.0,1.0);amin,amax=(min(av),max(av)) if av else (0.0,1.0)
    for idx,h in enumerate(horses):
        e=h.get('integratedEvaluation') or {};c=e.get('components') or {};pm=h.get('precomputedMetrics') or {};fit=pm.get('fit') or {};st=pm.get('style') or {}
        def cp(*names,default=.5):
            for name in names:
                if c.get(name) is not None:return _v207_norm01(c.get(name),default)
            return default
        try:samples=max(int(st.get('samples') or 0),int(e.get('samples') or 0))
        except (TypeError,ValueError):samples=0
        full=max(0.0,min(1.0,float(e.get('dataCompleteness') or 50)/100.0))
        evidence=max(0.0,min(1.0,.55*min(1.0,samples/5.0)+.45*full))
        runs=list(h.get('recentRaces') or [])[:5];finish_scores=[];gains=[];earlys=[];front_hold=[];wins=top3=used=0
        for rr in runs:
            try:fin=int(float(rr.get('finish') or rr.get('finishPosition') or 0))
            except (TypeError,ValueError):fin=0
            try:fs=max(2,int(float(rr.get('fieldSize') or 12)))
            except (TypeError,ValueError):fs=12
            if fin>0:
                score=max(0.0,min(1.0,1.0-(fin-1)/max(1,fs-1)));finish_scores.append(score);used+=1;wins+=int(fin==1);top3+=int(fin<=3)
            corners=rr.get('cornerPositions') or []
            if corners and fin>0:
                try:first=int(float(corners[0] or 0));last=int(float(corners[-1] or 0))
                except (TypeError,ValueError):first=last=0
                if last>0:gains.append(max(-1.0,min(1.0,(last-fin)/max(1,fs-1))))
                if first>0:earlys.append(max(0.0,min(1.0,1.0-(first-1)/max(1,fs-1))))
                if first>0:front_hold.append(1.0 if first<=3 and fin<=3 else 0.0)
        avg=sum(finish_scores)/len(finish_scores) if finish_scores else .5;peak=max(finish_scores) if finish_scores else .5;last=finish_scores[0] if finish_scores else .5
        no=int(h.get('horseNumber') or 0);w=weights[idx];age=ages[idx]
        f={
            'eval_score':_v207_norm01(e.get('score'),.5),'race_perf':cp('racePerformance'),'representative':cp('representative'),
            'distance':cp('distanceFit',default=_v207_norm01(fit.get('distance'),.5)),'track':cp('courseFit',default=_v207_norm01(fit.get('track'),.5)),
            'going':cp('goingFit',default=_v207_norm01(fit.get('condition'),.5)),'level':cp('opponentLevelScore',default=_v207_norm01(fit.get('level'),.5)),
            'lap':cp('lapScore'),'jockey':cp('jockeyScore','jockeyResults'),'trainer':cp('trainerScore','trainerResults'),'body':cp('bodyWeightScore'),
            'condition_change':cp('conditionChangeScore'),'ten':_v207_norm01(st.get('ten'),.5),'early3':_v207_norm01(st.get('early3'),0),
            'moved3':_v207_norm01(st.get('moved3'),0),'front':_v207_norm01(st.get('front'),0),'stalk':_v207_norm01(st.get('stalk'),0),
            'mid':_v207_norm01(st.get('mid'),0),'close':_v207_norm01(st.get('close'),0),'evidence':evidence,'data':full,
            'recent_win':wins/used if used else .1,'recent_top3':top3/used if used else .25,'recent_avg_finish':avg,'recent_peak_finish':peak,
            'recent_last_finish':last,'recent_gain':max(0.0,min(1.0,.5+.5*(sum(gains)/len(gains) if gains else 0.0))),
            'recent_early':sum(earlys)/len(earlys) if earlys else .5,'recent_front_hold':sum(front_hold)/len(front_hold) if front_hold else .25,
            'inside':1.0-(no-1)/max(1,field-1),'weight_rel':1.0-(w-wmin)/max(1e-6,wmax-wmin) if w is not None and wmax>wmin else .5,
            'age_rel':1.0-(age-amin)/max(1e-6,amax-amin) if age is not None and amax>amin else .5,
        }
        rows.append(f)
    rel_sources=['eval_score','race_perf','representative','distance','track','level','ten','early3','moved3','recent_avg_finish','recent_peak_finish','recent_top3']
    for name in rel_sources:
        ranks=_v213_rank_percentiles([f[name] for f in rows])
        for i,f in enumerate(rows):f['rel_'+name]=ranks[i]
    try:dist=float(detail.get('distance') or 1600)
    except (TypeError,ValueError):dist=1600
    short=max(0.0,min(1.0,(1800.0-dist)/600.0));long=max(0.0,min(1.0,(dist-1600.0)/800.0))
    for i,f in enumerate(rows):
        others=[z['early3'] for j,z in enumerate(rows) if j!=i];pressure=sum(others)/len(others) if others else .5;late=.42*f['moved3']+.32*f['mid']+.26*f['close']
        f['short_ten']=short*f['ten'];f['short_early3']=short*f['early3'];f['long_late']=long*late;f['front_conflict']=f['early3']*pressure;f['lone_front']=f['early3']*(1.0-pressure);f['late_role']=late
    return rows

