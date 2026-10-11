"""Legacy calculations with explicit dependencies; formulas preserved."""
from __future__ import annotations

from arvexq.prediction.legacy_model_tables import (V215_SPEED_BASE_DISTANCE_GOING, V215_SPEED_BASE_EXACT, V215_SPEED_BASE_TRACK_DISTANCE, V215_SPEED_GLOBAL, V215_DRAW_STATS, V215_TRACK_DRAW_STATS)


def _v215_speed_ratio(rr: dict) -> float | None:
    try:
        sec=float(rr.get('timeSeconds') or 0); dist=int(float(rr.get('distance') or 0))
    except (TypeError,ValueError):
        return None
    if sec <= 0 or dist <= 0:return None
    track=str(rr.get('track') or '');cond=str(rr.get('condition') or '不明');db=round(dist/200)*200
    base=(V215_SPEED_BASE_EXACT.get(f"{track}|{dist}|{cond}") or
          V215_SPEED_BASE_TRACK_DISTANCE.get(f"{track}|{dist}") or
          V215_SPEED_BASE_DISTANCE_GOING.get(f"{db}|{cond}") or V215_SPEED_GLOBAL)
    return max(.75,min(1.25,(dist/sec)/max(1e-9,float(base))))


def _v215_draw_score(track: str, dist: int, group: int) -> float:
    db=round(int(dist or 0)/200)*200
    arr=V215_DRAW_STATS.get(f"{track}|{db}")
    if not arr or sum(arr[:3]) < 24:arr=V215_TRACK_DRAW_STATS.get(str(track))
    if not arr or sum(arr[:3]) < 20:return .5
    starts=float(arr[group]);hits=float(arr[3+group]);total_s=float(sum(arr[:3]));total_h=float(sum(arr[3:]))
    base=(total_h+3)/(total_s+9);rate=(hits+1)/(starts+3);lift=rate/max(.05,base)
    return max(0.0,min(1.0,.5+.45*(lift-1)))

