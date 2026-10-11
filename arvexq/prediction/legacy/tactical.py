"""Legacy calculations with explicit dependencies; formulas preserved."""
from __future__ import annotations

from arvexq.prediction.legacy.common import _v213_zscore
from arvexq.prediction.legacy.professional import _v215_prof_feature_rows


V218_TACTICAL_MODEL_VERSION = "arvexq-seven-axis-overlay-v239"
V218_P1_BLEND = 0.24

def _v218_tactical_roles(detail: dict, horses: list[dict], base_rows: list[dict]):
    feats=_v215_prof_feature_rows(detail,horses,base_rows)
    field=max(1,len(feats))
    order=sorted(range(len(horses)), key=lambda i:int(horses[i].get('horseNumber') or i+1))
    early=[max(float(f.get('front',0)),float(f.get('stalk',0)),float(f.get('early3',0))) for f in feats]
    pressure=max(0.0,min(1.0,(sum(early)/field)*1.45))
    front_count=sum(1 for v in early if v>=.48)
    late_count=sum(1 for f in feats if float(f.get('late_role',0))>=.48)
    track_speed=detail.get('trackSpeed') or {}
    track_speed_score=max(0.0,min(1.0,float(track_speed.get('score') or .5)))
    track_speed_evidence=max(0.0,min(1.0,float(track_speed.get('evidence') or 0)))

    # Build multiple plausible race shapes instead of forcing one deterministic pace call.
    front_prob=max(.08,min(.58,.16+(1-pressure)*.24+(.10 if front_count==1 else 0.0)))
    collapse_prob=max(.08,min(.58,.10+pressure*.34+max(0,front_count-2)*.035))
    late_prob=max(.08,min(.34,.10+(late_count/field)*.16+pressure*.08))
    neutral_prob=max(.08,1.0-front_prob-collapse_prob-late_prob)
    psum=front_prob+collapse_prob+late_prob+neutral_prob
    front_prob/=psum;collapse_prob/=psum;late_prob/=psum;neutral_prob/=psum

    # Individual neighbour pressure by horse-number adjacency. This is deliberately
    # separate from overall pace pressure: a front horse can face a hard local squeeze
    # even in a race that is not globally extreme.
    neighbour=[{'left':0.0,'right':0.0,'sandwich':0.0,'local':0.0} for _ in feats]
    for pos,idx in enumerate(order):
        left=early[order[pos-1]] if pos>0 else 0.0
        right=early[order[pos+1]] if pos+1<len(order) else 0.0
        sandwich=1.0 if left>=.52 and right>=.52 else 0.0
        local=max(left,right,.5*(left+right))
        neighbour[idx]={'left':left,'right':right,'sandwich':sandwich,'local':local}

    p1_raw=[];p2_role=[];p3_role=[];audits=[]
    for i,f in enumerate(feats):
        nb=neighbour[i]
        pure=max(0.0,min(1.0,
            .24*f.get('eval_score',.5)+.18*f.get('race_perf',.5)+.16*f.get('representative',.5)+
            .10*f.get('level',.5)+.08*f.get('distance',.5)+.07*f.get('track',.5)+
            .06*f.get('going',.5)+.06*f.get('lap',.5)+.05*f.get('evidence',.5)
        ))

        # TRUE RUN approximates the performance hidden by finishing position. Early
        # effort, mid-race gain and adjusted speed can rescue a superficially poor run;
        # easy-front/conflict-free trips get less credit.
        effort_gap=f.get('recent_early',.5)-f.get('recent_last_finish',.5)
        gain=f.get('recent_gain',.5)-.5
        local_cost=max(0.0,min(1.0,.62*nb['local']+.38*nb['sandwich']))
        hidden=max(0.0,min(1.0,.50+.55*effort_gap+.25*gain-.15*f.get('lone_front',0)+.14*local_cost))
        true_run=max(0.0,min(1.0,
            .22*f.get('speed_adj_avg',.5)+.16*f.get('speed_adj_best',.5)+
            .15*f.get('speed_adj_last',.5)+.14*f.get('recency_wfinish',.5)+
            .10*f.get('finish_trend',.5)+.13*hidden+.10*f.get('class_fit',.5)
        ))

        # v300 robust live track-speed fit. A fast surface rewards horses that can sustain
        # raw speed/early position; a slow surface rewards TRUE RUN, late role and
        # going tolerance. Evidence controls the strength and neutralizes early races.
        fast_track_fit=max(0.0,min(1.0,.42*f.get('speed_adj_best',.5)+.28*f.get('speed_adj_avg',.5)+.18*f.get('ten',.5)+.12*f.get('early3',0)))
        slow_track_fit=max(0.0,min(1.0,.36*true_run+.27*f.get('late_role',0)+.21*f.get('going',.5)+.16*f.get('class_fit',.5)))
        if track_speed_score>=.52:track_speed_fit=fast_track_fit
        elif track_speed_score<=.48:track_speed_fit=slow_track_fit
        else:track_speed_fit=.5*(fast_track_fit+slow_track_fit)
        track_speed_intensity=min(1.0,abs(track_speed_score-.5)*2.0)*track_speed_evidence
        track_speed_fit=.5+(track_speed_fit-.5)*track_speed_intensity

        front_fit=max(0.0,min(1.0,
            .29*f.get('lone_front',0)+.23*f.get('recent_front_hold',.25)+
            .19*f.get('early3',0)+.13*f.get('ten',.5)+.10*(1-f.get('front_conflict',0))+
            .06*(1-local_cost)
        ))
        collapse_fit=max(0.0,min(1.0,
            .31*f.get('late_role',0)+.21*f.get('moved3',0)+.17*f.get('recent_gain',.5)+
            .13*f.get('close',0)+.11*f.get('speed_adj_best',.5)+.07*local_cost
        ))
        late_fit=max(0.0,min(1.0,
            .28*f.get('late_role',0)+.23*f.get('mid',0)+.19*f.get('close',0)+
            .15*f.get('finish_trend',.5)+.10*f.get('speed_adj_avg',.5)+.05*true_run
        ))
        neutral_fit=max(0.0,min(1.0,.55*pure+.23*f.get('pace_fit',.5)+.22*true_run))
        scenario=max(0.0,min(1.0,
            front_prob*front_fit+collapse_prob*collapse_fit+late_prob*late_fit+neutral_prob*neutral_fit
        ))
        scenario=max(0.0,min(1.0,scenario*(1-.04*track_speed_evidence)+track_speed_fit*(.04*track_speed_evidence)))

        # v238: "今回条件" is deliberately stronger, with more weight on the
        # race-specific facts (distance/course/going/class/draw) and less on
        # generic connections.  This is still bounded and evidence-regularized
        # downstream so one noisy condition cannot dominate the whole forecast.
        conditions=max(0.0,min(1.0,
            .18*f.get('distance',.5)+.15*f.get('track',.5)+.15*f.get('going',.5)+
            .14*f.get('class_fit',.5)+.10*f.get('draw_hist',.5)+.08*f.get('jockey_ctx',.5)+
            .06*f.get('trainer_ctx',.5)+.05*f.get('freshness',.5)+.04*f.get('weight_delta',.5)+
            .05*f.get('pace_fit',.5)
        ))
        conditions=max(0.0,min(1.0,conditions*(1-.06*track_speed_evidence)+track_speed_fit*(.06*track_speed_evidence)))
        evidence=max(0.0,min(1.0,.62*f.get('evidence',.5)+.38*f.get('style_reliability',.5)))

        # v239 seven-axis ability model.  The visible detail screen is intentionally
        # simple, but prediction keeps the full internal split: PURE / TRUE RUN /
        # SECTIONAL / pace fit / current conditions / opponent level / reproducibility.
        sectional=max(0.0,min(1.0,
            .55*f.get('lap',.5)+.25*f.get('speed_adj_avg',.5)+.20*f.get('speed_adj_best',.5)
        ))
        opponent=max(0.0,min(1.0,.62*f.get('level',.5)+.38*f.get('class_fit',.5)))
        reproducibility=max(0.0,min(1.0,
            .30*evidence+.18*f.get('recency_wfinish',.5)+.14*f.get('finish_trend',.5)+
            .14*f.get('weight_stability',.5)+.12*f.get('style_reliability',.5)+
            .12*f.get('speed_evidence',.5)
        ))
        # Keep the user's strengthened current-condition stance (22%) while
        # separating the other six concepts instead of hiding them inside one score.
        p1_score=(.21*pure+.17*true_run+.12*sectional+.14*scenario+.22*conditions+
                  .08*opponent+.06*reproducibility)
        p1_score=.5+(p1_score-.5)*(.58+.42*evidence)
        p1_raw.append(p1_score)

        # Role compatibility is not a replacement for the validated P2/P3 marginal
        # models. It is emitted for the conditional-order engine to use after a winner
        # or winner+runner-up has been fixed.
        second=max(0.0,min(1.0,
            .23*true_run+.22*f.get('pace_fit',.5)+.18*f.get('recent_front_hold',.5)+
            .15*f.get('moved3',.5)+.12*conditions+.10*(1-.55*local_cost)
        ))
        third=max(0.0,min(1.0,
            .22*true_run+.21*f.get('late_role',.5)+.17*f.get('moved3',.5)+
            .14*f.get('close',.5)+.14*conditions+.12*evidence
        ))
        p2_role.append(second);p3_role.append(third)
        audits.append({
            'pure':round(pure,4),'trueRun':round(true_run,4),'hiddenEffort':round(hidden,4),
            'sectional':round(sectional,4),'positionScenario':round(scenario,4),'conditions':round(conditions,4),
            'opponentLevel':round(opponent,4),'stateConsistency':round(reproducibility,4),'sevenAxisScore':round(p1_score,4),
            'trackSpeedFit':round(track_speed_fit,4),'trackSpeed':{'score':round(track_speed_score,4),'evidence':round(track_speed_evidence,4),'ratio':track_speed.get('ratio',1.0),'label':track_speed.get('label','基準'),'completed':track_speed.get('completed',0)},
            'secondRole':round(second,4),'thirdRole':round(third,4),'evidence':round(evidence,4),
            'positionPressure':{
                'left':round(nb['left'],4),'right':round(nb['right'],4),
                'local':round(nb['local'],4),'sandwich':bool(nb['sandwich'])
            },
            'scenarioProbabilities':{
                'front':round(front_prob,4),'neutral':round(neutral_prob,4),
                'collapse':round(collapse_prob,4),'late':round(late_prob,4)
            }
        })
    return _v213_zscore(p1_raw),p2_role,p3_role,audits

