from __future__ import annotations

from collections import defaultdict
from math import isfinite
from typing import Any, Iterable

SELECTION_VERSION = "arvexq-mass-feature-selection-v1"

# Keep the broad factory exploratory, but freeze only a disciplined candidate set.
# This prevents feature-name/payload explosion and removes obvious correlated copies
# before any label-driven model selection happens.
HISTORY_SUBSETS = {
    "all",
    "same_track",
    "same_surface",
    "same_condition",
    "same_track_surface",
    "matched_clock_context",
    "distance_200",
    "same_track_distance_200",
    "same_surface_distance_200",
}
HISTORY_STATS = {
    "count",
    "mean",
    "median",
    "max",
    "last",
    "std",
    "q75",
    "trend",
    "latest_minus_mean",
}
RELATIVE_SUFFIXES = {"percentile", "leader_gap"}


def _history_allowed(name: str) -> bool:
    parts = name.split("::")
    # history::<subset>::wX::<metric>::<stat> OR run_count
    if len(parts) == 4 and parts[0] == "history" and parts[3] == "run_count":
        return parts[1] in HISTORY_SUBSETS
    if len(parts) != 5 or parts[0] != "history":
        return False
    return parts[1] in HISTORY_SUBSETS and parts[4] in HISTORY_STATS


def snapshot_feature_allowed(name: str) -> bool:
    if name.startswith(("static::", "market::", "category::", "delta::")):
        return True
    if name.startswith("history::"):
        return _history_allowed(name)
    if name.startswith("relative::"):
        parts = name.rsplit("::", 1)
        if len(parts) != 2 or parts[1] not in RELATIVE_SUFFIXES:
            return False
        base = parts[0][len("relative::"):]
        if base.startswith("history::"):
            # Relative copies are useful mainly for central tendency / current form,
            # not for every count/std/quantile derivative.
            bparts = base.split("::")
            return (
                len(bparts) == 5
                and bparts[1] in HISTORY_SUBSETS
                and bparts[4] in {"mean", "median", "max", "last", "trend"}
            )
        return base.startswith(("static::", "market::", "delta::"))
    return False


def prune_feature_dict(features: dict[str, float]) -> dict[str, float]:
    return {name: value for name, value in features.items() if snapshot_feature_allowed(str(name))}


def prune_matrix_for_snapshot(matrix: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out=[]
    for row in matrix:
        copied=dict(row)
        copied["features"]=prune_feature_dict(row.get("features") or {})
        copied["featureCount"]=len(copied["features"])
        copied["featureSelectionVersion"]=SELECTION_VERSION
        out.append(copied)
    return out


def choose_training_manifest(
    rows: Iterable[dict[str, Any]],
    *,
    min_coverage: float = 0.01,
    max_features: int = 8000,
) -> list[str]:
    """Unsupervised first-stage training prune using TRAIN rows only.

    Scores features by coverage × variance. Constant, ultra-sparse and non-finite
    columns are removed before label-aware model fitting. This is deliberately fit
    only on the chronological training block by the caller.
    """
    rows=list(rows)
    n=max(1,len(rows))
    count=defaultdict(int)
    sums=defaultdict(float)
    sums2=defaultdict(float)
    for row in rows:
        feats=row.get("modelFeatures") or row.get("features") or {}
        for name,value in feats.items():
            try:x=float(value)
            except (TypeError,ValueError):continue
            if not isfinite(x):continue
            key=str(name);count[key]+=1;sums[key]+=x;sums2[key]+=x*x
    ranked=[]
    for name,c in count.items():
        coverage=c/n
        if coverage<min_coverage:continue
        mean=sums[name]/c
        var=max(0.0,sums2[name]/c-mean*mean)
        if var<=1e-12:continue
        # Preserve meaningful rare categories without letting one-hot cardinality dominate.
        bonus=1.15 if name.startswith("category::") else 1.0
        ranked.append((coverage*(var**0.5)*bonus,name))
    ranked.sort(key=lambda x:(-x[0],x[1]))
    return [name for _,name in ranked[:max(100,int(max_features))]]


def restrict_features(features: dict[str,float], manifest: set[str]) -> dict[str,float]:
    return {k:v for k,v in features.items() if k in manifest}
