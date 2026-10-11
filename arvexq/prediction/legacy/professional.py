"""Legacy calculations with explicit dependencies; formulas preserved."""
from __future__ import annotations

import math
from datetime import date as dt_date
from arvexq.prediction.legacy.common import _v207_norm01, _v213_zscore
from arvexq.prediction.legacy.course import _v215_draw_score, _v215_speed_ratio
from arvexq.prediction.legacy_model_tables import V215_FEATURES, V215_MEAN, V215_P1_COEF, V215_SCALE


def _v215_prof_feature_rows(detail: dict, horses: list[dict], base_rows: list[dict]) -> list[dict]:
    rows=[];field=max(1,len(horses))
    try:target_date=dt_date.fromisoformat(str(detail.get('date') or ''))
    except Exception:target_date=None
    for idx,h in enumerate(horses):
        f=dict(base_rows[idx]);runs=list(h.get('recentRaces') or [])[:5]
        finish_scores=[];wf_num=wf_den=0.0;speed_vals=[];speed_ws=[];carried=[];prizes=[];days=[]
        for j,rr in enumerate(runs):
            wrec=.72**j
            try:fin=int(float(rr.get('finish') or rr.get('finishPosition') or 0))
            except (TypeError,ValueError):fin=0
            try:fs=max(2,int(float(rr.get('fieldSize') or 12)))
            except (TypeError,ValueError):fs=12
            if fin>0:
                score=max(0.0,min(1.0,1.0-(fin-1)/max(1,fs-1)));finish_scores.append(score);wf_num+=score*wrec;wf_den+=wrec
            sr=_v215_speed_ratio(rr)
            if sr is not None:speed_vals.append(sr);speed_ws.append(wrec)
            try:
                cw=float(rr.get('carriedWeight'))
                if math.isfinite(cw):carried.append(cw)
            except (TypeError,ValueError):pass
            try:
                rp=float(rr.get('racePrize1') or 0)
                if rp>0:prizes.append(rp)
            except (TypeError,ValueError):pass
            if target_date and rr.get('date'):
                try:days.append(max(0,(target_date-dt_date.fromisoformat(str(rr.get('date')))).days))
                except Exception:pass
        trend=(finish_scores[0]-(sum(finish_scores[1:])/len(finish_scores[1:]) if len(finish_scores)>1 else finish_scores[0])) if finish_scores else 0.0
        spavg=sum(v*w for v,w in zip(speed_vals,speed_ws))/sum(speed_ws) if speed_vals else 1.0
        spbest=max(speed_vals) if speed_vals else 1.0;splast=speed_vals[0] if speed_vals else 1.0
        sptrend=(speed_vals[0]-(sum(speed_vals[1:])/len(speed_vals[1:]) if len(speed_vals)>1 else speed_vals[0])) if speed_vals else 0.0
        curpr=float(detail.get('racePrize1') or 0);prevpr=(sum(prizes)/len(prizes) if prizes else 0.0);bestpr=max(prizes) if prizes else 0.0
        class_drop=.5 if curpr<=0 or prevpr<=0 else max(0.0,min(1.0,.5+.22*math.log(max(1e-6,prevpr/curpr))))
        class_fit=.5 if curpr<=0 or bestpr<=0 else max(0.0,min(1.0,.5+.20*math.log(max(1e-6,bestpr/curpr))))
        try:curw=float(h.get('carriedWeight'));curw=curw if math.isfinite(curw) else float('nan')
        except (TypeError,ValueError):curw=float('nan')
        lastw=carried[0] if carried else curw
        wd=0.0 if not (math.isfinite(curw) and math.isfinite(lastw)) else curw-lastw
        weight_delta=max(0.0,min(1.0,.5-.08*wd));wstd=float(np.std(carried)) if False else (math.sqrt(sum((x-sum(carried)/len(carried))**2 for x in carried)/len(carried)) if len(carried)>=2 else 0.0)
        jp=h.get('jockeyProfile') or {};tp=h.get('trainerProfile') or {}
        def pv(p,key,default=.5):return _v207_norm01(p.get(key),default)
        jctx=sum(pv(jp,k) for k in ('overall','track','distance','condition'))/4.0;tctx=sum(pv(tp,k) for k in ('overall','track','distance','condition'))/4.0
        no=int(h.get('horseNumber') or 0);q=(no-1)/max(1,field-1);grp=0 if q<.34 else (2 if q>.66 else 1)
        f.update({
            'speed_adj_avg':max(0.0,min(1.0,.5+(spavg-1)*3.2)),'speed_adj_best':max(0.0,min(1.0,.5+(spbest-1)*2.8)),
            'speed_adj_last':max(0.0,min(1.0,.5+(splast-1)*3.0)),'speed_adj_trend':max(0.0,min(1.0,.5+sptrend*5)),
            'speed_evidence':min(1.0,len(speed_vals)/5.0),'recency_wfinish':wf_num/wf_den if wf_den else .5,
            'finish_trend':max(0.0,min(1.0,.5+trend*.8)),'days_since_last':min(1.0,(days[0] if days else 90)/180.0),
            'freshness':max(0.0,min(1.0,1-abs((days[0] if days else 45)-28)/120.0)),'class_drop':class_drop,'class_fit':class_fit,
            'weight_delta':weight_delta,'weight_stability':max(0.0,min(1.0,1-wstd/4.0)),'jockey_ctx':jctx,'jockey_track':pv(jp,'track'),
            'jockey_distance':pv(jp,'distance'),'jockey_condition':pv(jp,'condition'),'jockey_front':pv(jp,'early3Rate'),
            'trainer_ctx':tctx,'trainer_track':pv(tp,'track'),'trainer_distance':pv(tp,'distance'),'trainer_condition':pv(tp,'condition'),
            'draw_hist':_v215_draw_score(str(detail.get('track') or ''),int(float(detail.get('distance') or 1600)),grp),
            'live_draw':.5,'live_style':.5,'field_norm':max(0.0,min(1.0,(field-4)/12.0)),
            'style_reliability':min(1.0,max(int((h.get('precomputedMetrics') or {}).get('style',{}).get('samples') or 0),int((h.get('integratedEvaluation') or {}).get('samples') or 0))/5.0),
        })
        rows.append(f)
    for i,f in enumerate(rows):
        others=[z.get('early3',0) for j,z in enumerate(rows) if j!=i];pressure=sum(others)/len(others) if others else .5
        late=.42*f.get('moved3',0)+.32*f.get('mid',0)+.26*f.get('close',0);early=max(f.get('front',0),f.get('stalk',0),f.get('early3',0))
        f['pace_fit']=max(0.0,min(1.0,early*(1-pressure)+late*pressure))
    return rows


def _v215_professional_p1(detail: dict, horses: list[dict], base_rows: list[dict]) -> list[float]:
    feats=_v215_prof_feature_rows(detail,horses,base_rows);raw=[]
    for f in feats:
        total=0.0
        for i,name in enumerate(V215_FEATURES):
            total += V215_P1_COEF[i]*((f.get(name,.5)-V215_MEAN[i])/max(1e-9,V215_SCALE[i]))
        raw.append(total)
    return _v213_zscore(raw)

