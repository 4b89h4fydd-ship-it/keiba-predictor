"""Legacy calculations with explicit dependencies; formulas preserved."""
from __future__ import annotations

from arvexq.prediction.legacy_model_tables import V207_WINNER_WEIGHTS, V212_P2_MODEL_COEFFICIENTS, V212_P2_MODEL_INTERCEPT
from arvexq.prediction.legacy.common import _v207_component, _v207_norm01
import math


def _v207_winner_score(horse: dict, legacy_p1: float) -> float:
    """v206 holdout-promoted winner ranker, used only on validated circuits.

    The feature whitelist exactly mirrors backtest_v206.py. Result, payout,
    win odds and popularity are deliberately absent.
    """
    e=horse.get("integratedEvaluation") or {}
    pm=horse.get("precomputedMetrics") or {}
    fit=pm.get("fit") or {}
    st=pm.get("style") or {}
    try:samples=max(int(st.get("samples") or 0),int(e.get("samples") or 0))
    except (TypeError,ValueError):samples=0
    fullness=max(0.0,min(1.0,float(e.get("dataCompleteness") or 50)/100.0))
    evidence=max(0.0,min(1.0,.55*min(1.0,samples/5.0)+.45*fullness))
    late_role=max(0.0,min(1.0,
        .42*_v207_norm01(st.get("moved3"),0)+
        .32*_v207_norm01(st.get("mid"),0)+
        .26*_v207_norm01(st.get("close"),0)))
    f={
        "p1_saved":_v207_norm01(legacy_p1,.5),
        "eval_score":_v207_norm01(e.get("score"),.5),
        "race_perf":_v207_component(e,"racePerformance",default=.5),
        "representative":_v207_component(e,"representative",default=.5),
        "distance":_v207_component(e,"distanceFit",default=_v207_norm01(fit.get("distance"),.5)),
        "track":_v207_component(e,"courseFit",default=_v207_norm01(fit.get("track"),.5)),
        "going":_v207_component(e,"goingFit",default=_v207_norm01(fit.get("condition"),.5)),
        "level":_v207_component(e,"opponentLevelScore",default=_v207_norm01(fit.get("level"),.5)),
        "lap":_v207_component(e,"lapScore",default=.5),
        "jockey":_v207_component(e,"jockeyScore","jockeyResults",default=.5),
        "trainer":_v207_component(e,"trainerScore","trainerResults",default=.5),
        "body":_v207_component(e,"bodyWeightScore",default=.5),
        "condition_change":_v207_component(e,"conditionChangeScore",default=.5),
        "early3":_v207_norm01(st.get("early3"),0),
        "ten":_v207_norm01(st.get("ten"),.5),
        "late_role":late_role,
        "evidence":evidence,
    }
    return round(max(0.0,min(1.0,sum(V207_WINNER_WEIGHTS[k]*f[k] for k in V207_WINNER_WEIGHTS)))*100,4)


def _v212_role_feature_map(horse: dict) -> dict[str,float]:
    e=horse.get("integratedEvaluation") or {}
    c=e.get("components") or {}
    pm=horse.get("precomputedMetrics") or {}
    fit=pm.get("fit") or {}
    st=pm.get("style") or {}
    try:samples=max(0,int(st.get("samples") or 0))
    except (TypeError,ValueError):samples=0
    def comp(*names,default=.5):
        for name in names:
            if c.get(name) is not None:return _v207_norm01(c.get(name),default)
        return default
    return {
        "base":_v207_norm01(e.get("score"),.5),
        "perf":comp("racePerformance"),
        "rep":comp("representative"),
        "dist":_v207_norm01(fit.get("distance"),.5),
        "track":_v207_norm01(fit.get("track"),.5),
        "going":_v207_norm01(fit.get("condition"),.5),
        "level":_v207_norm01(fit.get("level"),.5),
        "jockey":comp("jockeyScore","jockeyResults"),
        "trainer":comp("trainerScore","trainerResults"),
        "body":comp("bodyWeightScore"),
        "lap":comp("lapScore"),
        "ten":_v207_norm01(st.get("ten"),.5),
        "early3":_v207_norm01(st.get("early3"),.0),
        "moved3":_v207_norm01(st.get("moved3"),.0),
        "front":_v207_norm01(st.get("front"),.0),
        "stalk":_v207_norm01(st.get("stalk"),.0),
        "mid":_v207_norm01(st.get("mid"),.0),
        "close":_v207_norm01(st.get("close"),.0),
        "evidence":max(0.0,min(1.0,samples/5.0)),
        "data":_v207_norm01(e.get("dataCompleteness"),.5),
    }


def _v212_p2_score(horse: dict) -> float:
    """Validated local-racing second-place role ranker.

    Trained chronologically on the same market-blind evidence fields used by ARVEXQ.
    It is deliberately not used for JRA until the JRA holdout is available.
    """
    f=_v212_role_feature_map(horse)
    z=V212_P2_MODEL_INTERCEPT+sum(V212_P2_MODEL_COEFFICIENTS[k]*f[k] for k in V212_P2_MODEL_COEFFICIENTS)
    z=max(-40.0,min(40.0,z))
    prob=1.0/(1.0+math.exp(-z))
    return round(prob*100.0,4)

