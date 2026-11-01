"""Frozen lane configuration for the rewrite engine.

One configuration serves both the pre-off sealing lane (forward
validation record) and the production publish lane, so what the app
displays is exactly what the sealed record later grades. The lane only
changes at an explicit version boundary: when a candidate configuration
has beaten this one on unseen races, bump the model key and the frozen
weights together. Never drift silently.

Version boundary (2026-11-01): the v8 candidate (margin-weighted Elo
+ speed index v2, rewrite/analysis/shadow_v8.py) was adopted for the
PRODUCTION publish lane after the 2026-11-01 first forward verdict
(same-137 logloss v1 2.1492 vs v8 2.0145, 95%CI for the difference
[-0.1924, -0.0718]). From 2026-11-01 onward, races that have not yet
started get the v8 ability layer for the jra_flat and nar segments
whenever the shadow lane's exported extras are available (see
V8_CUTOVER_DATE in scripts/arvexq_rewrite_publish.py). LANE_WEIGHTS
below remain in force for the other segments and as the fallback
whenever v8 extras are unavailable. The frozen v1 seal series is
unchanged: the sealing lane keeps sealing with this configuration so
the forward record stays a single consistent series.
"""
from __future__ import annotations

LANE_BETA = 2.0

# Ability-prior v1 weights per segment (the exact weights in force when
# the first seals were made on 2026-10-28).
LANE_WEIGHTS = {
    "jra_flat": {
        "form": 0.30, "speed": 0.20, "distance": 0.10, "track": 0.05,
        "surface": 0.10, "condition": 0.05, "jockey": 0.10,
        "closing": 0.05, "consistency": 0.05,
    },
    "nar": {
        "form": 0.32, "speed": 0.20, "distance": 0.10, "track": 0.08,
        "surface": 0.05, "condition": 0.05, "jockey": 0.10,
        "closing": 0.05, "consistency": 0.05,
    },
    "jumps": {
        "form": 0.35, "speed": 0.10, "distance": 0.10, "track": 0.10,
        "surface": 0.05, "condition": 0.05, "jockey": 0.10,
        "closing": 0.05, "consistency": 0.10,
    },
    "debut": {},
}
