"""Legacy calculations with explicit dependencies; formulas preserved."""
from __future__ import annotations

import math


def _v313_horse_flow_adjust(h:dict, profile:dict, field:int)->float:
    if not profile or not profile.get("active"):return 0.0
    runs=list(h.get("recentRaces") or h.get("allPastRuns") or [])[:5];early=late=den=0.0
    for j,rr in enumerate(runs):
        if not isinstance(rr,dict):continue
        cp=[]
        for v in (rr.get("cornerPositions") or []):
            try:q=int(v)
            except Exception:q=0
            if q>0:cp.append(q)
        if not cp:continue
        try:fs=max(4,int(rr.get("fieldSize") or 12))
        except Exception:fs=12
        w=.78**j;pos=cp[0];norm=(pos-1)/max(3,fs-1);den+=w
        if pos<=max(2,math.ceil(fs*.25)):early+=w
        elif norm>=.55:late+=w
        if len(cp)>1 and cp[-1]<=max(3,math.ceil(fs*.30)) and pos>max(3,math.ceil(fs*.30)):late+=w*.35
    if den<=0:early=late=.5
    else:early/=den;late=min(1.0,late/den)
    try:fr=int(h.get("frameNumber") or 0)
    except Exception:fr=0
    max_frame=max(2,min(8,math.ceil(max(2,field)/2)));inside=max(0.0,min(1.0,1-(fr-1)/max(1,max_frame-1))) if fr else .5
    raw=float(profile.get("frontSignal") or 0)*(early-late)+float(profile.get("lateSignal") or 0)*(late-early)+float(profile.get("innerSignal") or 0)*(inside-.5)*1.35
    return max(-.06,min(.06,raw))


def _v317_factor_weights(detail:dict, sparse:bool=False)->dict[str,float]:
    central=str(detail.get('circuit') or '')=='中央'
    if central:
        w={'ability':.12,'classLevel':.06,'form':.07,'pace':.14,'suitability':.23,'connections':.18,'pedigree':.20} if sparse else {'ability':.26,'classLevel':.12,'form':.14,'pace':.18,'suitability':.16,'connections':.08,'pedigree':.06}
    else:
        w={'ability':.10,'classLevel':.06,'form':.07,'pace':.18,'suitability':.25,'connections':.20,'pedigree':.14} if sparse else {'ability':.24,'classLevel':.08,'form':.16,'pace':.20,'suitability':.18,'connections':.09,'pedigree':.05}
    def shift(a,b,x):w[a]+=x;w[b]-=x
    try:dist=float(detail.get('distance') or 0)
    except Exception:dist=0
    surface=str(detail.get('surface') or '')
    if dist and dist<=1400:shift('pace','pedigree',.025);shift('ability','classLevel',.015)
    elif dist>=2300:shift('suitability','pace',.030);shift('classLevel','form',.015)
    if 'ダ' in surface:shift('pace','pedigree',.020);shift('suitability','ability',.015)
    if not central:shift('pace','classLevel',.015);shift('suitability','pedigree',.010)
    total=sum(max(.01,v) for v in w.values()) or 1.0
    return {k:max(.01,v)/total for k,v in w.items()}


def _v317_factor_profile(detail:dict, horse:dict)->dict:
    e=horse.get('integratedEvaluation') or {};c=e.get('components') if isinstance(e.get('components'),dict) else {};a=e.get('v218Audit') or e.get('v217Audit') or {};pm=horse.get('precomputedMetrics') or {};fit=pm.get('fit') or {};st=pm.get('style') or {}
    def u(v,default=.5):
        try:
            x=float(v)
            if not math.isfinite(x):return default
            if x>1.5:x/=100.0
            return max(0.0,min(1.0,x))
        except Exception:return default
    def ax(key,default=.5):return u(a.get(key),default)
    def comp(names,default=.5):
        for k in names:
            if c.get(k) is not None:return u(c.get(k),default)
        return u(default,.5)
    runs=(horse.get('recentRaces') or horse.get('allPastRuns') or [])[:5];tot=good=0
    for rr in runs:
        if not isinstance(rr,dict):continue
        try:f=int(rr.get('finish') or rr.get('finishPosition') or rr.get('rank') or 0)
        except Exception:f=0
        if f>0:tot+=1;good+=1 if f<=3 else 0
    recent=good/tot if tot else .5
    pp=a.get('positionPressure') if isinstance(a.get('positionPressure'),dict) else {}
    frag=u(pp.get('local'),0)
    pure=ax('pure',u(e.get('score'),.5));tr=ax('trueRun',.5);sec=ax('sectional',comp(['lapScore'],.5));scen=ax('positionScenario',.5);cond=ax('conditions',.5);opp=ax('opponentLevel',comp(['opponentLevelScore'],u(fit.get('level'),.5)));state=ax('stateConsistency',.5)
    perf=comp(['racePerformance'],.5);rep=comp(['representative'],.5);course=comp(['courseFit'],u(fit.get('track'),.5));dist=comp(['distanceFit'],u(fit.get('distance'),.5));going=comp(['goingFit'],u(fit.get('condition'),.5));level=comp(['opponentLevelScore'],opp);lap=comp(['lapScore'],sec)
    jockey=comp(['jockeyScore','jockeyResults'],.5);trainer=comp(['trainerScore','trainerResults'],.5);body=comp(['bodyWeightScore'],.5);change=comp(['conditionChangeScore'],.5);ped=comp(['pedigreeScore'],.5);ds=comp(['distanceSuitabilityScore'],dist);ss=comp(['surfaceSuitabilityScore'],.5);draw=comp(['drawScore'],.5)
    ten=u(st.get('ten'),.5);moved=u(st.get('moved3'),.0);close=u(st.get('close'),.0);pace_extra=.55*ten+.25*moved+.20*close
    ability=max(0,min(1,.28*pure+.27*tr+.17*sec+.16*perf+.12*rep))
    class_level=max(0,min(1,.46*opp+.26*level+.16*u(fit.get('level'),.5)+.12*perf))
    form=max(0,min(1,.30*state+.26*recent+.24*perf+.12*rep+.08*(1-frag)))
    pace=max(0,min(1,.36*scen+.18*lap+.18*pace_extra+.15*state+.13*(1-frag)))
    suitability=max(0,min(1,.16*cond+.17*course+.17*dist+.13*going+.12*ds+.09*ss+.08*draw+.08*u(fit.get('track'),.5)))
    connections=max(0,min(1,.33*jockey+.25*trainer+.19*body+.15*change+.08*state))
    pedigree=max(0,min(1,.52*ped+.28*ds+.20*ss))
    sparse=bool(e.get('neutralPrior')) or int(e.get('samples') or 0)<2
    weights=_v317_factor_weights(detail,sparse);factors={'ability':ability,'classLevel':class_level,'form':form,'pace':pace,'suitability':suitability,'connections':connections,'pedigree':pedigree}
    score=sum(weights[k]*factors[k] for k in weights);central=str(detail.get('circuit') or '')=='中央';win=max(0,min(1,score*(1-(.13 if central else .08)*frag)));place=max(0,min(1,.28*score+.20*form+.20*pace+.18*suitability+.08*connections+.06*(1-frag)));show=max(0,min(1,.22*score+.22*form+.20*suitability+.16*pace+.08*connections+.07*pedigree+.05*(1-frag)))
    return {'factors':factors,'weights':weights,'score':score,'win':win,'place':place,'show':show,'fragility':frag,'sparse':sparse,'evidence':ax('evidence',u(e.get('dataCompleteness'),.5))}

