"""Restore a tombstoned detail's forecast blocks from its sealed product.

Incident (2026-11-23): during the morning recovery, eleven of today's
published races (plus Tokyo 3R on the JRA side) had their STORED D1
details overwritten with the API projection's shape —
``predictionStatus="disabled"`` / ``predictionModelVersion=
"arvexq-prediction-removed"`` with the ``prediction`` /
``predictionMarks`` / ``recommendedBets`` blocks stripped.  The sealed
unified product (``unifiedForecast``) and the publish lane's marker
survived untouched in the same stored detail, and the product's
receipt (sha256 over its canonical form) still verifies.

The protect guard (``scripts/arvexq_protect_sync.py``) could not heal
this: its only restore source was the pre-off stage64 archive, which
lives in the worker's read envelope and is absent from both the plain
read and the stored detail, so every lane failed closed and the
forecasts stayed unrestorable.

This module rebuilds the publish lane's derived blocks from the
sealed product itself, using the lane's own deterministic rules:

- ``predictionMarks`` — verbatim from the product's marks (the sealed
  assignment; verified byte-identical against a healthy stored race).
- ``prediction.stages.probability`` — the product's ``diagnosis``
  carries every runner's win / top-3 probability (the publish lane's
  own surgical upgrades read the same source).
- ``recommendedBets`` — regenerated with the lane's own ticket
  generator (``rewrite.analysis.tickets.generate_tickets``) from the
  sealed probabilities.  Plackett-Luce strengths are recoverable from
  the win probabilities (the distribution is scale-invariant), and
  the regeneration is SELF-VERIFIED against the sealed
  ``ticketPlan``: the sealed items must reappear, in order and with
  equal probabilities, as the head of the regenerated per-kind
  ranking.  Any mismatch fails closed (returns ``None``).  The sealed
  probabilities were computed from full-precision strengths while the
  diagnosis carries win probabilities rounded to 4dp, so regenerated
  ticket probabilities can drift by ~0.0001; the self-check therefore
  binds the combinations and their order exactly and the
  probabilities within 0.002.  The restored blocks store
  combinations, not these probabilities, so the drift never reaches
  the restored content.
- ``prediction`` — reassembled with the exact construction
  ``build_publish_detail`` uses for the v9b lane (constants mirrored
  below and pinned by tests against the publish module).

Nothing is re-sealed and nothing is estimated: the product, its
receipt and the lane marker are carried over untouched, and only
inputs sealed before the off are used, so restoring a race after its
start reconstructs the pre-off record — it never derives anything
from results.

Acceptance is deliberately narrow (fail closed otherwise):

- the detail is projection-tombstone shaped;
- the product verifies (``unified_product.verified``) and its receipt
  equals the lane marker's receipt, and the marker's ``publishedAt``
  equals the product's ``capturedAt``;
- the marker is one of the publish lane's known ability lanes
  (``v9b-cal-market`` / ``v8-elo-speed2`` / ``v1-prior`` — the jumps
  lane), whose prediction-block shapes are mirrored from
  ``build_publish_detail``; any other lane fails closed;
- the diagnosis covers the product's runner set (a scratched runner
  stays on the card but is not part of the sealed forecast) with
  probabilities summing to ~1, and the ticket self-check above
  passes.
"""
from __future__ import annotations

import copy
from typing import Any

# Mirrors of scripts/arvexq_rewrite_publish.py constants (the publish
# module imports the protect guard, so importing it here would cycle;
# tests pin these against the publish module's own values).
ABILITY_STATUS_V9B = "rewrite-ability-elo-speed2-v9b"
ABILITY_STATUS_V8 = "rewrite-ability-elo-speed2-v8"
ABILITY_STATUS_PRIOR = "rewrite-ability-prior-v1"
PACE_STAGE_STATUS = "past-corner-evidence-uncalibrated"
TICKETS_STAGE_STATUS = "probability-only-ev-suppressed"
METHODOLOGY_STATUS_V9B = "rewrite-engine-probability-calibrated-market-blend"
CALIBRATION_METHOD_V9B = "temperature-0.6692+geometric-market-blend-0.5"
METHODOLOGY_STATUS_UNCALIBRATED = "rewrite-engine-probability-uncalibrated"
CALIBRATION_METHOD_UNCALIBRATED = "none-probabilities-uncalibrated"
BET_REASON = ("同一モデルの結合確率上位。期待値は券種別実オッズ不足と"
              "確率校正未検証のため表示しない")
COMBO_KINDS = {"wide": "ワイド", "quinella": "馬連", "exacta": "馬単",
               "trio": "3連複", "trifecta": "3連単"}
# The publish lane's ability lanes (marker ``abilityLane``) and the
# prediction-block shape build_publish_detail stamps for each.  Any
# other lane value fails closed: its block shape is not guessed.
LANE_SHAPES = {
    "v9b-cal-market": (METHODOLOGY_STATUS_V9B, CALIBRATION_METHOD_V9B,
                       ABILITY_STATUS_V9B),
    "v8-elo-speed2": (METHODOLOGY_STATUS_UNCALIBRATED,
                      CALIBRATION_METHOD_UNCALIBRATED, ABILITY_STATUS_V8),
    "v1-prior": (METHODOLOGY_STATUS_UNCALIBRATED,
                 CALIBRATION_METHOD_UNCALIBRATED, ABILITY_STATUS_PRIOR),
}


def _formation(detail: dict[str, Any], marker: dict[str, Any]) -> str | None:
    """The trifecta formation the lane sealed for this race."""
    formation = marker.get("ticketFormation")
    if isinstance(formation, dict) and formation.get("formation"):
        return str(formation["formation"])
    circuit = str(detail.get("circuit") or "")
    if circuit == "地方":
        return "P4A2"
    if circuit == "中央":
        return "R24"
    return None


def _regenerate_tickets(detail: dict[str, Any],
                        product: dict[str, Any],
                        formation: str):
    """Regenerate the lane's probability tickets from the sealed product.

    Returns the TicketPlan, or None when the sealed inputs cannot
    support it or the regeneration disagrees with the sealed
    ticketPlan (the self-check that keeps this a restore, not a
    recomputation with drifted rules).
    """
    from rewrite.analysis.forecast import RaceForecast, RunnerForecast
    from rewrite.analysis.tickets import generate_tickets

    # The runner set is the product's own diagnosis set, NOT the
    # detail's card: a scratched runner stays on the card but is not
    # part of the sealed forecast (verified() binds the roster to the
    # active runners), and the original blocks were built from the
    # forecast's runners only.
    diagnosis = {}
    for entry in product.get("diagnosis") or []:
        if isinstance(entry, dict) and isinstance(
                entry.get("horseNumber"), int):
            diagnosis[entry["horseNumber"]] = entry
    if len(diagnosis) < 3:
        return None
    names = {h.get("horseNumber"): h.get("name")
             for h in detail.get("horses") or [] if isinstance(h, dict)}
    mark_by_no = {m.get("horseNumber"): m for m in product.get("marks") or []
                  if isinstance(m, dict)}
    runners = []
    win_total = 0.0
    for number in sorted(diagnosis):
        entry = diagnosis[number]
        win = entry.get("winProbability")
        top3 = entry.get("top3Probability")
        if (not isinstance(win, (int, float)) or isinstance(win, bool)
                or not isinstance(top3, (int, float))
                or isinstance(top3, bool)):
            return None
        win_total += float(win)
        runners.append(RunnerForecast(
            number=number, name=names.get(number) or "",
            ability_score=entry.get("abilityScore"),
            strength=float(win), pace_adjustment=0.0, pace_reasons=(),
            p_win=float(win), p_top2=None, p_top3=float(top3),
            mark=(mark_by_no.get(number) or {}).get("markSymbol", ""),
            status="ok"))
    if not 0.99 <= win_total <= 1.01:
        return None
    forecast = RaceForecast(
        race_id=str(detail.get("id") or ""), beta=0.0,
        probability_status=product.get("probabilityStatus"),
        runners=tuple(runners), status="ok")
    try:
        plan = generate_tickets(
            forecast, {}, calibration_validated=False,
            trifecta_formation=formation, place_odds={})
    except Exception:
        return None
    # Self-check: every sealed ticketPlan item must reappear as the
    # head of the regenerated ranking for its kind, with the same
    # combination and the same (4dp) probability.  The sealed plan is
    # the capped head of the very ranking being regenerated, so any
    # drift in inputs or rules breaks the prefix and fails closed.
    sealed_items = (product.get("ticketPlan") or {}).get("items") or []
    if not sealed_items:
        return None
    regenerated: dict[str, list] = {}
    for ticket in plan.probability_tickets:
        label = COMBO_KINDS.get(ticket.kind)
        if label:
            regenerated.setdefault(label, []).append(ticket)
    sealed_by_kind: dict[str, list] = {}
    for item in sealed_items:
        if isinstance(item, dict) and item.get("kind"):
            sealed_by_kind.setdefault(str(item["kind"]), []).append(item)
    for kind, items in sealed_by_kind.items():
        ranking = regenerated.get(kind) or []
        if len(ranking) < len(items):
            return None
        for item, ticket in zip(items, ranking):
            if list(ticket.selection) != [int(n) for n in item.get("combo") or []]:
                return None
            sealed_probability = item.get("probability")
            if (isinstance(sealed_probability, (int, float))
                    and abs(float(ticket.probability)
                            - float(sealed_probability)) > 0.002):
                return None
    return plan


def sealed_product_restore(detail: Any) -> dict[str, Any] | None:
    """Rebuild a tombstoned detail's forecast blocks from its product.

    Returns a restored deep copy of ``detail``, or ``None`` when the
    sealed original cannot be verified (the caller keeps failing
    closed, exactly as before this restore existed).
    """
    if not isinstance(detail, dict):
        return None
    from scripts.arvexq_protect_sync import _projection_tombstone
    if not _projection_tombstone(detail):
        return None
    from arvexq.prediction.unified_product import MODEL_VERSION, verified
    product = verified(detail)
    if product is None:
        return None
    meta = detail.get("preparedMeta") or {}
    marker = meta.get("rewritePublish") or {}
    if not isinstance(marker, dict):
        return None
    if marker.get("modelVersion") != MODEL_VERSION:
        return None
    if marker.get("receiptSha256") != product.get("receiptSha256"):
        return None
    if marker.get("publishedAt") != product.get("capturedAt"):
        return None
    lane_shape = LANE_SHAPES.get(str(marker.get("abilityLane") or ""))
    if lane_shape is None:
        return None
    methodology_status, calibration_method, ability_status = lane_shape
    formation = _formation(detail, marker)
    if formation is None:
        return None
    plan = _regenerate_tickets(detail, product, formation)
    if plan is None:
        return None
    forecast_text = detail.get("forecastText")
    if not isinstance(forecast_text, str) or not forecast_text:
        return None
    diagnosis = {entry.get("horseNumber"): entry
                 for entry in product.get("diagnosis") or []
                 if isinstance(entry, dict)}
    win_map: dict[str, Any] = {}
    top3_map: dict[str, Any] = {}
    for number in sorted(diagnosis):
        entry = diagnosis[number]
        win_map[str(number)] = entry.get("winProbability")
        top3_map[str(number)] = entry.get("top3Probability")
    marks = [{"horseNumber": m.get("horseNumber"),
              "mark": m.get("markSymbol"),
              "winProbability": m.get("winProbability")}
             for m in product.get("marks") or []]
    grouped: dict[str, list] = {}
    for ticket in plan.probability_tickets:
        if ticket.kind in COMBO_KINDS:
            grouped.setdefault(COMBO_KINDS[ticket.kind], []).append(
                list(ticket.selection))
    recommended = [
        {"kind": kind, "combos": combos, "points": len(combos),
         "reason": BET_REASON}
        for kind, combos in grouped.items()]
    prediction = {
        "raceId": detail.get("id"), "date": detail.get("date"),
        "circuit": detail.get("circuit"),
        "capturedAt": product.get("capturedAt"),
        "methodologyStatus": methodology_status,
        "actualForecasterPublishedPicks": True,
        "calibrationMethod": calibration_method,
        "modelVersion": MODEL_VERSION,
        "predictionStatus": "ready", "productionEligible": True,
        "stages": {
            "ability": {"status": ability_status},
            "pace": {"status": PACE_STAGE_STATUS, "text": forecast_text},
            "probability": {"value": {"win": win_map, "top3": top3_map}},
            "marks": {"value": {"orderedWinCandidates":
                                [m["horseNumber"] for m in marks]}},
            "tickets": {"status": TICKETS_STAGE_STATUS},
        },
        "predictionMarks": marks,
        "recommendedBets": recommended,
        "methodWeights": {}, "methodEvidence": {}, "calibrationRaces": 0,
        "forecastText": forecast_text,
        "humanOverrideAllowed": False,
    }
    restored = copy.deepcopy(detail)
    restored["prediction"] = prediction
    restored["predictionMarks"] = marks
    restored["recommendedBets"] = recommended
    restored["predictionStatus"] = "ready"
    restored["predictionModelVersion"] = MODEL_VERSION
    return restored
