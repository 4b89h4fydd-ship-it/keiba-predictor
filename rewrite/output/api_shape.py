"""Adapter from rewrite engine records to the production UI payload shapes.

The existing frontend (arvexq/ui/static) consumes two payload families:

- ``GET /api/day?date=`` -> ``{ok, date, races: [...]}`` where each race
  row is camelCase (id, date, circuit, track, raceNumber, startTime,
  title, surface, distance, weather, condition, raceStatus,
  updatedAtEpoch).
- ``GET /api/race/<id>`` -> ``{ok, race_id, summary, analysis_ready,
  odds, detail}`` where ``detail`` carries the camelCase race fields,
  ``horses``, ``predictionMarks``, ``recommendedBets`` and
  ``unifiedForecast``.

Honesty rules enforced here:

- Flags are fixed truthful values: probabilities are NOT calibrated,
  output is research-only, and no human override exists.
- Expected value is never emitted: the tickets layer suppresses EV
  while calibration is unvalidated, so every EV field is null and the
  suppression reason is carried in text the UI surfaces.
- Probability *ranges* are null. The engine produces point estimates
  from a single model; a fabricated interval would claim scenario
  evidence we do not have. Point probabilities ride along in the
  ``winProbability`` / ``top3Probability`` fields instead.
- ``receiptSha256`` is the SHA-256 of the stored raw source snapshot
  this payload was derived from (verifiable against the rewrite
  Store). It is input provenance, NOT a sealed pre-off prediction
  receipt. ``modelHash`` is the SHA-256 of the canonical model
  parameter set actually used (ability weights, beta, pace constants).
  Both are genuinely computed; neither is a production fusion receipt.
  When provenance is unavailable both are null and the frontend's
  unified-forecast gate fails closed, exactly as it should.
"""
from __future__ import annotations

import hashlib
import json
from datetime import timezone
from typing import Optional

from ..analysis.ability import MODEL_VERSION as ABILITY_MODEL_VERSION
from ..analysis.ability import SEGMENT_WEIGHTS
from ..analysis.forecast import (
    FLOOR_FRACTION,
    PACE_CLOSER_BOOST,
    PACE_FRONT_CROWD_PENALTY,
    PACE_LONE_FRONT_BOOST,
    RaceForecast,
)
from ..analysis.pace import PaceForecast
from ..analysis.tickets import TicketPlan
from ..data.normalize import Obs, PastRun, RaceRecord, RunnerRecord
from ..safety.contracts import Segment

UNIFIED_VERSION = "arvexq-unified-live-v1"
ADAPTER_VERSION = "arvexq-rewrite-output-v1"
MODEL_VERSION = "arvexq-rewrite-v1-uncalibrated-prior"
# The serving beta was fitted on the 2026-10-21..2026-10-23 training
# slice only (time-ordered backtest). Races on/before that window must
# not be presented as pre-off forecasts of this model, so the same date
# is exported as trainedThrough and the UI gate enforces it.
BETA_FIT_THROUGH = "2026-10-23"

PROBABILITIES_CALIBRATED = False
RESEARCH_ONLY = True
HUMAN_OVERRIDES = False

KIND_LABELS = {
    "win": "単勝", "place": "複勝", "wide": "ワイド", "quinella": "馬連",
    "exacta": "馬単", "trio": "3連複", "trifecta": "3連単",
}
# Kinds the frontend ticket lane renders from unifiedForecast.ticketPlan.
UI_TICKET_KINDS = ("quinella", "exacta", "wide", "trio", "trifecta")
MAX_UI_TICKET_ITEMS = 5
# Engine stage key -> production paceStages key.
STAGE_KEYS = {
    "start": "start", "corner3": "turn3", "corner4": "turn4",
    "straight": "straight",
}
MARK_ORDER = ("◎", "○", "▲", "△", "☆")


def _value(obs: Obs, default=None):
    return obs.value if obs.present else default


def _epoch(obs: Obs) -> int:
    if obs.present:
        try:
            return int(obs.value.timestamp())
        except (AttributeError, ValueError, OSError):
            return 0
    return 0


def model_hash(beta: float) -> str:
    """SHA-256 of the canonical parameter set used for a forecast."""
    params = {
        "adapter": ADAPTER_VERSION,
        "modelVersion": MODEL_VERSION,
        "abilityModelVersion": ABILITY_MODEL_VERSION,
        "segmentWeights": {
            segment.value: weights
            for segment, weights in sorted(
                SEGMENT_WEIGHTS.items(), key=lambda kv: kv[0].value
            )
        },
        "beta": beta,
        "floorFraction": FLOOR_FRACTION,
        "paceAdjustments": {
            "frontCrowdPenalty": PACE_FRONT_CROWD_PENALTY,
            "closerBoost": PACE_CLOSER_BOOST,
            "loneFrontBoost": PACE_LONE_FRONT_BOOST,
        },
    }
    blob = json.dumps(params, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


# ---------------------------------------------------------------- day


def _day_row(race: RaceRecord) -> dict:
    return {
        "id": race.race_id,
        "date": race.date,
        "circuit": _value(race.circuit, ""),
        "track": race.track,
        "raceNumber": _value(race.race_number),
        "startTime": _value(race.start_time, ""),
        "title": _value(race.title, ""),
        # Production day rows use "" for an unpublished surface and the
        # literal 不明 for unpublished weather/condition; mirror that.
        "surface": _value(race.surface, ""),
        "distance": _value(race.distance),
        "weather": _value(race.weather, "不明"),
        "condition": _value(race.condition, "不明"),
        "raceStatus": "",
        "updatedAtEpoch": _epoch(race.updated_at),
    }


def day_payload(date: str, races: list[RaceRecord]) -> dict:
    """Production /api/day shape (list rows only; details stay per-race)."""
    rows = [_day_row(race) for race in races if race.date == date]
    return {
        "ok": True,
        "date": date,
        "races": rows,
        "details": [],
        "complete": False,
        "raceCount": len(rows),
        "source": ADAPTER_VERSION,
    }


# -------------------------------------------------------------- horses


def _past_run(row: PastRun) -> dict:
    return {
        "date": row.date,
        "track": _value(row.track),
        "distance": _value(row.distance),
        "surface": _value(row.surface),
        "condition": _value(row.condition),
        "weather": _value(row.weather),
        "finish": _value(row.finish),
        "fieldSize": _value(row.field_size),
        "cornerPositions": list(row.corner_positions),
        "timeSeconds": _value(row.time_seconds),
        "timeBehindWinner": _value(row.time_behind_winner),
        "marginSeconds": _value(row.margin_seconds),
        "marginText": _value(row.margin_text),
        "jockey": _value(row.jockey),
        "carriedWeight": _value(row.carried_weight),
    }


def _horse(runner: RunnerRecord, segment: Segment) -> dict:
    runs = [_past_run(run) for run in runner.past_runs]
    return {
        "id": _value(runner.horse_id),
        "horseNumber": runner.number,
        "frameNumber": _value(runner.frame_number),
        "name": _value(runner.name, ""),
        "age": _value(runner.age),
        "sex": _value(runner.sex),
        "carriedWeight": _value(runner.carried_weight),
        "jockey": _value(runner.jockey),
        "trainer": _value(runner.trainer),
        "status": "出走取消" if runner.scratched else "",
        "scratched": runner.scratched,
        "winOdds": _value(runner.win_odds),
        "bodyWeight": _value(runner.body_weight),
        "bodyWeightChange": _value(runner.body_weight_change),
        # The UI merges recentRaces/allPastRuns and filters to runs
        # strictly before the race date; the normalizer already
        # enforced that, so both views carry the same evidence.
        "recentRaces": runs,
        "allPastRuns": runs,
        "debutNoHistory": segment is Segment.DEBUT and not runs,
    }


# ---------------------------------------------------------------- pace


def _lane(runner: Optional[RunnerRecord], field_size: int) -> int:
    """Lateral lane -2..2 from the gate (frame) position, inside to out."""
    frame = None
    if runner is not None and runner.frame_number.present:
        frame = runner.frame_number.value
    if not isinstance(frame, (int, float)) or frame < 1:
        return 0
    # Frames run 1..8 in JRA/NAR cards regardless of field size.
    lane = round((min(frame, 8) - 1) / 7 * 4) - 2
    return max(-2, min(2, lane))


def _pace_stages(race: RaceRecord, pace: PaceForecast) -> list[dict]:
    by_number = {r.number: r for r in race.runners}
    stages = []
    for engine_key in ("start", "corner3", "corner4", "straight"):
        order = pace.stages[engine_key].order
        pack = [
            {"no": number, "lane": _lane(by_number.get(number), pace.field_size)}
            for number, _ratio in order
        ]
        stages.append({"key": STAGE_KEYS[engine_key], "pack": pack})
    return stages


def _pace_block(race: RaceRecord, pace: PaceForecast) -> dict:
    names = {r.number: _value(r.name, "") for r in race.runners}
    front = list(pace.front_runners)
    if front:
        listed = "、".join(f"{n}番{names.get(n, '')}" for n in front)
        text = f"{pace.pace_label}。過去走の初角位置から前に行く候補は{listed}。"
    else:
        text = "過去走の初角位置の観測不足につき先行候補は未確認。"
    return {
        "status": "past-corner-evidence-uncalibrated",
        "likelyForwardNumbers": front,
        "observedPositionCoverage": pace.field_size - len(pace.unknown_runners),
        "activeRunners": pace.field_size,
        "unknownNumbers": list(pace.unknown_runners),
        "pacePressure": pace.pace_pressure,
        "paceLabel": pace.pace_label,
        "testedScenarios": ["normal", "fast", "slow"],
        "scenarioFrequencyMeasured": False,
        "firstCornerMetersOfficial": None,
        "text": text,
    }


# --------------------------------------------------------------- marks


def _mark_reason(runner_forecast) -> str:
    parts = []
    if runner_forecast.p_win is not None:
        parts.append(
            f"勝率推定{runner_forecast.p_win * 100:.1f}%"
            f"・3着内推定{runner_forecast.p_top3 * 100:.1f}%（未校正）"
        )
    for reason in runner_forecast.pace_reasons:
        parts.append(f"展開補正:{reason}")
    if runner_forecast.status == "unscored-floor-strength":
        parts.append("過去走の証拠不足のため下限確率で評価")
    return "／".join(parts)


def _marks(forecast: RaceForecast) -> tuple[list[dict], list[dict], Optional[int]]:
    """(predictionMarks, unifiedForecast.marks, honmei number)."""
    marked = [r for r in forecast.runners if r.mark]
    marked.sort(key=lambda r: MARK_ORDER.index(r.mark))
    prediction_marks = [
        {
            "horseNumber": r.number,
            "mark": r.mark,
            "winProbability": r.p_win,
        }
        for r in marked
    ]
    unified_marks = [
        {
            "horseNumber": r.number,
            "markSymbol": r.mark,
            # Point estimates only: no scenario range is fabricated.
            "winProbabilityRange": None,
            "top3ProbabilityRange": None,
            "winProbability": r.p_win,
            "top3Probability": r.p_top3,
            "reason": _mark_reason(r),
        }
        for r in marked
    ]
    honmei = next((r.number for r in marked if r.mark == "◎"), None)
    return prediction_marks, unified_marks, honmei


def _diagnosis_reason(runner_forecast) -> str:
    text = _mark_reason(runner_forecast)
    if runner_forecast.ability_score is None:
        note = "過去走の証拠不足のため能力スコアなし"
        return f"{text}／{note}" if text else note
    return text


def _diagnosis(forecast: RaceForecast) -> list[dict]:
    """All-runner diagnosis block for the 全頭診断 panel.

    Marks carry probabilities for the five marked runners only; the
    diagnosis panel renders EVERY runner, so it needs the engine's
    per-runner ability score and probabilities for the whole field.
    Values are the engine's own: the ability layer's raw score in
    [0, 1] (never the win probability), the Plackett-Luce point
    probabilities, and the same reason text the marks carry. A runner
    the engine could not score keeps nulls, not invented values.
    """
    return [
        {
            "horseNumber": r.number,
            "abilityScore": r.ability_score,
            "winProbability": r.p_win,
            "top3Probability": r.p_top3,
            "reason": _diagnosis_reason(r),
        }
        for r in forecast.runners
    ]


# ------------------------------------------------------------- tickets


def _ticket_reason(plan: TicketPlan) -> str:
    if plan.probability_tickets:
        base = (
            "未校正の確率による参考候補。確率校正が未検証のため期待値は"
            "算出せず、購入推奨ではありません"
        )
    else:
        base = "確率候補が基準に達しないため見送り"
    suppressed = plan.suppressed or {}
    notes = []
    if suppressed.get("ev_win") == "calibration-not-validated":
        notes.append("単勝の期待値は確率未校正のため抑制")
    if any(str(k).startswith("ev_") and v == "odds-unavailable"
           for k, v in suppressed.items()):
        notes.append("複合券種は発走前の実オッズ不足のため期待値を算出しない")
    if "forecast" in suppressed:
        notes.append(f"予想自体が未成立: {suppressed['forecast']}")
    return "。".join([base, *notes])


def _ticket_plan_block(plan: TicketPlan) -> dict:
    items = [
        {
            "kind": KIND_LABELS[ticket.kind],
            "combo": list(ticket.selection),
            "probability": ticket.probability,
        }
        for ticket in plan.probability_tickets
        if ticket.kind in UI_TICKET_KINDS
    ]
    items.sort(key=lambda item: (-item["probability"], item["combo"]))
    items = items[:MAX_UI_TICKET_ITEMS]
    return {
        "status": "参考候補" if items else "見送り",
        "items": items,
        "reason": _ticket_reason(plan),
        "sameModelAndMarks": True,
        "maximumPoints": MAX_UI_TICKET_ITEMS,
        "expectedValue": None,
        "expectedValueStatus": "suppressed-calibration-not-validated",
        "suppressed": {k: str(v) for k, v in (plan.suppressed or {}).items()},
    }


def _recommended_bets(plan: TicketPlan) -> list[dict]:
    """Full probability-ticket list in the bet_view plan-item shape."""
    reason = _ticket_reason(plan)
    bets = []
    for ticket in plan.probability_tickets:
        bets.append({
            "kind": KIND_LABELS[ticket.kind],
            "combos": [list(ticket.selection)],
            "points": 1,
            "level": "参考候補",
            "reason": reason,
            "comboProbabilities": [round(ticket.probability * 100, 1)],
            "probability": ticket.probability,
            "odds": ticket.odds,
            "oddsStatus": ticket.odds_status,
            # The tickets layer allows no EV while calibration is
            # unvalidated; keep the field present and explicitly null.
            "expectedValue": None,
            "stakeUnits": None,
        })
    # EV-lane tickets exist only when the tickets layer produced them
    # (validated calibration); include them verbatim if ever present.
    for ticket in plan.ev_tickets:
        bets.append({
            "kind": KIND_LABELS[ticket.kind],
            "combos": [list(ticket.selection)],
            "points": 1,
            "level": "期待値",
            "reason": "校正済み確率と実オッズによる期待値候補",
            "comboProbabilities": [round(ticket.probability * 100, 1)],
            "probability": ticket.probability,
            "odds": ticket.odds,
            "oddsStatus": ticket.odds_status,
            "expectedValue": ticket.expected_return,
            "stakeUnits": ticket.stake_units,
        })
    return bets


# ---------------------------------------------------------------- race


def _summary_row(race: RaceRecord) -> dict:
    """Snake-case summary row, mirroring the production /api/race body."""
    return {
        "race_id": race.race_id,
        "race_date": race.date,
        "circuit": _value(race.circuit, ""),
        "track": race.track,
        "race_no": _value(race.race_number),
        "start_time": _value(race.start_time, ""),
        "title": _value(race.title, ""),
        "surface": _value(race.surface, ""),
        "distance": _value(race.distance),
        "weather": _value(race.weather, "不明"),
        "condition": _value(race.condition, "不明"),
        "race_status": "",
        "updated_at": _epoch(race.updated_at),
    }


def race_payload(
    race: RaceRecord,
    forecast: RaceForecast,
    pace: PaceForecast,
    tickets: TicketPlan,
    *,
    provenance: Optional[dict] = None,
) -> dict:
    """Production /api/race/<id> envelope for one rewrite forecast.

    ``provenance`` may carry ``snapshot_sha256`` (SHA-256 of the stored
    raw source snapshot), ``captured_at`` (ISO timestamp of that
    snapshot) and ``odds`` (the production odds rows, passed through
    untouched). Without provenance the receipt fields are null and the
    frontend's unified gate fails closed.
    """
    provenance = provenance or {}
    prediction_marks, unified_marks, honmei = _marks(forecast)
    circuit = _value(race.circuit, "")
    start_time = _value(race.start_time, "")
    unified = {
        "version": UNIFIED_VERSION,
        "raceId": race.race_id,
        "raceDate": race.date,
        "circuit": circuit,
        "modelFamily": "jumps" if race.segment is Segment.JUMPS else "flat",
        "specialHandling": (
            "新馬" if race.segment is Segment.DEBUT
            else "障害" if race.segment is Segment.JUMPS
            else "通常"
        ),
        "capturedAt": provenance.get("captured_at"),
        "trainedThrough": BETA_FIT_THROUGH,
        "modelVersion": MODEL_VERSION,
        "modelHash": model_hash(forecast.beta),
        "adapterVersion": ADAPTER_VERSION,
        "abilityModelVersion": ABILITY_MODEL_VERSION,
        "beta": forecast.beta,
        "probabilityStatus": forecast.probability_status,
        "forecastStatus": forecast.status,
        "roster": [
            {"horseNumber": r.number, "name": _value(r.name, "")}
            for r in race.runners
        ],
        "marks": unified_marks,
        "diagnosis": _diagnosis(forecast),
        "honmeiHorseNumber": honmei,
        "pace": _pace_block(race, pace),
        "paceStages": _pace_stages(race, pace),
        "ticketPlan": _ticket_plan_block(tickets),
        "analysisStages": {
            "ability": {"status": "prior-weights-unfitted",
                        "modelVersion": ABILITY_MODEL_VERSION},
            "pace": {"status": "past-corner-evidence-uncalibrated"},
            "probability": {"status": forecast.probability_status,
                            "calibrated": PROBABILITIES_CALIBRATED},
            "marks": {"status": "mechanical-from-probability"},
            "tickets": {"status": "probability-only-ev-suppressed"},
        },
        "researchOnly": RESEARCH_ONLY,
        "probabilitiesCalibrated": PROBABILITIES_CALIBRATED,
        "humanOverrides": HUMAN_OVERRIDES,
        "source": ADAPTER_VERSION,
        # Input provenance only: SHA-256 of the stored raw snapshot.
        # Not a sealed pre-off prediction receipt (see module docstring).
        "receiptSha256": provenance.get("snapshot_sha256"),
        "receiptKind": "source-snapshot-sha256",
    }
    detail = {
        "id": race.race_id,
        "circuit": circuit,
        "date": race.date,
        "track": race.track,
        "raceNumber": _value(race.race_number),
        "title": _value(race.title, ""),
        "distance": _value(race.distance),
        "surface": _value(race.surface, ""),
        "weather": _value(race.weather, "不明"),
        "condition": _value(race.condition, "不明"),
        "fieldSize": len(race.runners),
        "startTime": start_time,
        "scheduledStartTime": start_time,
        "horses": [_horse(r, race.segment) for r in race.runners],
        "result": None,
        "source": race.source,
        "predictionStatus": forecast.probability_status,
        "predictionModelVersion": MODEL_VERSION,
        "prediction": None,
        "predictionMarks": prediction_marks,
        "recommendedBets": _recommended_bets(tickets),
        "forecastText": _pace_block(race, pace)["text"],
        "unifiedForecast": unified,
    }
    return {
        "ok": True,
        "race_id": race.race_id,
        "summary": _summary_row(race),
        "analysis_ready": forecast.status == "ok",
        "detail_updated_at": (
            race.updated_at.value.astimezone(timezone.utc).isoformat()
            if race.updated_at.present else None
        ),
        "odds": provenance.get("odds") or [],
        "detail": detail,
    }
