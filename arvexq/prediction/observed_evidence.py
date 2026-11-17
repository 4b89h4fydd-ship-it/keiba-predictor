"""Compute the observed mineta/margin evidence scores read by attach_evidence.

These are the same two observed quantities the retired 60/40 observed model
used before its mark/ranking authority was deleted (git history:
arvexq/prediction/observed_model.py @ 0d2d7761):

- mineta: field-aware positioning proxy from past corner positions
  (arvexq.research.mineta_field_proxy.score_race), 0..1.
- margin: measured-margin ABCDE candidate score
  (arvexq.research.margin_abcde_candidate.score), 0..1, whose factor A is the
  recency-weighted exp(-seconds behind winner). Missing margins are never
  replaced with finish ranks.

This module only *computes evidence*. It never ranks horses, assigns marks,
or feeds probabilities: the scores surface exclusively through
``integratedEvaluation.narModelEvidence`` -> ``researchEvidence.factors``
(see race_intelligence.attach_evidence) and the analysis-basis panel.
Observed research staying out of live predictions is the standing rule
(tests/test_nar_mineta_margin_authority.py).

Circuit rules kept from the retired model:
- JRA flat and obstacle histories are never mixed when scoring a JRA race.
- A JRA margin counts only when tied to an official result proof
  (marginEvidence with winner/horse times from a JRA/official source).

Horses without the underlying observations keep no score (None), so the
factors card honestly renders available=false for them.
"""
from __future__ import annotations

import math
import re
from typing import Any

from arvexq.core.runner_status import is_inactive_runner
from arvexq.prediction.past_performance import observed_runs
from arvexq.research.margin_abcde_candidate import score as _margin_score
from arvexq.research.mineta_field_proxy import score_race as _mineta_scores

RUN_KEYS = ("recentRaces", "allPastRuns", "pastRaces", "history", "runs")
JRA_CIRCUITS = ("中央", "JRA", "central")


def _is_jra(race: dict[str, Any]) -> bool:
    return str(race.get("circuit") or "") in JRA_CIRCUITS


def _is_obstacle(run: dict[str, Any]) -> bool:
    return bool(re.search(r"障害|ジャンプ|\bJS\b|J[・･.]?G",
                          str(run.get("surface") or "") + str(run.get("title") or "")))


def _course_history(horse: dict[str, Any], race: dict[str, Any]) -> dict[str, Any]:
    """JRA flat/jump are not comparable; avoid mixing unrelated starts."""
    if not _is_jra(race):
        return horse
    jump = _is_obstacle(race) or str(race.get("analysisMode") or "") == "障害"
    out = dict(horse)
    for key in RUN_KEYS:
        if isinstance(horse.get(key), list):
            out[key] = [x for x in horse[key]
                        if isinstance(x, dict) and _is_obstacle(x) == jump]
    return out


def _verified_jra_proof(run: dict[str, Any]) -> bool:
    """JRA margins must be tied to observed official results, not an estimate."""
    v = run.get("marginSeconds", run.get("timeBehindWinner"))
    if v is None or v == "":
        return False
    try:
        if not math.isfinite(float(v)):
            return False
    except (ValueError, TypeError):
        return False
    proof = run.get("marginEvidence")
    source = str(run.get("marginEvidenceSource") or "").lower()
    return (isinstance(proof, dict)
            and proof.get("winnerTimeSeconds") is not None
            and proof.get("horseTimeSeconds") is not None
            and ("jra" in source or "official" in source))


def _margin_for(scoring_horse: dict[str, Any], detail: dict[str, Any]) -> dict[str, Any] | None:
    if _is_jra(detail):
        # Only official JRA result evidence qualifies, including genuine 0.0.
        past = observed_runs(scoring_horse, detail, limit=5)
        valid = [q for q in past if _verified_jra_proof(q)]
        if not valid:
            return None
        restricted = dict(scoring_horse)
        for key in RUN_KEYS:
            restricted[key] = valid
        return _margin_score(restricted, detail)
    return _margin_score(scoring_horse, detail)


def _fill(horse: dict[str, Any], scoring_horse: dict[str, Any],
          detail: dict[str, Any], mineta_map: dict[int, float]) -> None:
    container = horse.get("integratedEvaluation")
    if not isinstance(container, dict):
        container = {}
        horse["integratedEvaluation"] = container
    existing = container.get("narModelEvidence")
    if not isinstance(existing, dict):
        existing = {}

    mineta = existing.get("mineta")
    if mineta is None:
        try:
            mineta = mineta_map.get(int(horse.get("horseNumber") or 0))
        except (TypeError, ValueError):
            mineta = None

    margin = existing.get("margin")
    margin_coverage = existing.get("marginCoverage")
    if margin is None:
        result = _margin_for(scoring_horse, detail)
        if result is not None:
            margin = result.get("score")
            margin_coverage = result.get("coverage")

    if mineta is None and margin is None:
        # No observation behind either factor: stay honestly unavailable
        # instead of writing an empty or neutral evidence record.
        return

    sample = existing.get("sample")
    if sample is None:
        sample = len(observed_runs(scoring_horse, detail, limit=5))
    container["narModelEvidence"] = {
        "mineta": mineta,
        "margin": margin,
        "marginCoverage": margin_coverage,
        "sample": sample,
    }


def attach_model_evidence(detail: dict[str, Any]) -> dict[str, Any]:
    """Fill integratedEvaluation.narModelEvidence from observed past runs.

    Pre-existing non-null factor values are preserved; only missing factors
    are computed. Evidence computation must never block delivery, so any
    scoring failure leaves the horse's evidence untouched (unavailable).
    """
    if not isinstance(detail, dict):
        return detail
    horses = [h for h in detail.get("horses") or []
              if isinstance(h, dict) and h.get("horseNumber")]
    if not horses:
        return detail
    active = [h for h in horses if not is_inactive_runner(h)]
    active_ids = {id(h) for h in active}
    scoring = {id(h): _course_history(h, detail) for h in horses}
    try:
        mineta_map = _mineta_scores([scoring[id(h)] for h in active], detail)
    except Exception:
        mineta_map = {}
    if not isinstance(mineta_map, dict):
        mineta_map = {}
    for horse in horses:
        try:
            _fill(horse, scoring[id(horse)], detail,
                  mineta_map if id(horse) in active_ids else {})
        except Exception:
            continue
    return detail
