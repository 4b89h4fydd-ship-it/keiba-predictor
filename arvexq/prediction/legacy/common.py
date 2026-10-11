"""Legacy calculations with explicit dependencies; formulas preserved."""
from __future__ import annotations

import math


def _v207_norm01(value, default=.5):
    try:
        x=float(value)
        if not math.isfinite(x): return default
    except (TypeError,ValueError):
        return default
    if x > 1.5: x /= 100.0
    return max(0.0,min(1.0,x))


def _v207_component(e: dict, *names: str, default=.5):
    c=e.get("components") or {}
    for name in names:
        if c.get(name) is not None:
            return _v207_norm01(c.get(name),default)
    return default


def _v213_rank_percentiles(values):
    n=len(values)
    if n<=1:return [0.5]*n
    out=[]
    for v in values:
        less=sum(1 for x in values if x < v)
        equal=sum(1 for x in values if x == v)
        rank=1.0+less+(equal-1)*0.5
        out.append((rank-1.0)/(n-1.0))
    return out


def _v213_zscore(values):
    if not values:return []
    mean=sum(values)/len(values)
    var=sum((x-mean)**2 for x in values)/len(values)
    sd=math.sqrt(var)
    if sd<1e-9:return [0.0 for _ in values]
    return [(x-mean)/sd for x in values]


def _v213_softmax(values):
    if not values:return []
    mx=max(values);ex=[math.exp(max(-60.0,min(60.0,x-mx))) for x in values];s=sum(ex) or 1.0
    return [x/s for x in ex]

