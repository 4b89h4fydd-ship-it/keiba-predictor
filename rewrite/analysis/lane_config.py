"""Frozen lane configuration for the rewrite engine.

One configuration serves both the pre-off sealing lane (forward
validation record) and the production publish lane, so what the app
displays is exactly what the sealed record later grades. The lane only
changes at an explicit version boundary: when a candidate configuration
has beaten this one on unseen races, bump the model key and the frozen
weights together. Never drift silently.
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
