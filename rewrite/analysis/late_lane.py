"""Late-information lane (yukochi-imitation S2, shadow only).

The frozen v1 lane seals the night before with whatever the card
carried at that hour: body weight is normally absent (measured
0/533 runners at seal time), the going is still the early value,
and scratches or jockey changes after sealing never reach it.
yukochi's Nankan model re-issues its forecast once, about 30
minutes before the off, with the day's body weight and going
folded in. This module is the ARVEXQ shadow version of that idea:

- ``late_inputs_from_api_payload`` distils a production-API race
  payload (detail + summary + odds rows, fetched at T-30) into the
  late facts that exist at that moment. Nothing is interpolated:
  a missing body weight stays missing.
- ``apply_late_inputs`` folds those facts into the ingest-day
  ``RaceRecord`` (scratches, jockey changes, summary going/weather,
  body weight and its change, win odds at fetch time) so the frozen
  lane configuration can be re-scored on the field as it actually
  stands. Body weight is recorded on the record and in the seal
  context; the frozen v1 weights carry no body-weight feature, so
  it does not move scores in this lane — its measured effect is
  left to the fitted-variant verdict (see the S1/S2' backtest).
- ``gate_open`` reads the Phase 0 availability audit summary: the
  lane seals nothing until the audit's pre-registered gates pass.

This module never touches the v1 seal store or production
payloads; the runner seals into its own shadow store.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Optional

from ..data.normalize import Obs, RaceRecord, RunnerRecord, obs

LATE_SOURCE = "late-api-t30"
UNKNOWN_VALUES = {None, "", "不明", "未定", "-", "なし"}


@dataclass(frozen=True)
class LateInputs:
    """Late facts for one race, keyed by runner number."""

    condition: Optional[str] = None
    weather: Optional[str] = None
    scratched: dict[int, bool] = field(default_factory=dict)
    jockey: dict[int, str] = field(default_factory=dict)
    body_weight: dict[int, float] = field(default_factory=dict)
    body_weight_change: dict[int, float] = field(default_factory=dict)
    win_odds: dict[int, float] = field(default_factory=dict)
    popularity: dict[int, int] = field(default_factory=dict)

    def body_weight_coverage(self, numbers: list[int]) -> float:
        if not numbers:
            return 0.0
        got = sum(1 for n in numbers if n in self.body_weight)
        return got / len(numbers)


def _present(value) -> bool:
    return value not in UNKNOWN_VALUES and value != 0


def late_inputs_from_api_payload(payload: dict) -> LateInputs:
    """Distil one production-API /api/race/<id> payload.

    Mirrors the Phase 0 audit's field routing: body weight and odds
    come from detail.horses with the top-level odds rows as the
    second channel; going/weather come from the top-level summary
    (the detail side keeps the early "不明" values).
    """
    detail = payload.get("detail") or {}
    summary = payload.get("summary") or {}
    odds_by_no = {}
    for row in payload.get("odds") or []:
        if isinstance(row, dict) and row.get("horse_no") is not None:
            odds_by_no[row["horse_no"]] = row

    late = LateInputs(
        condition=summary.get("condition")
        if summary.get("condition") not in UNKNOWN_VALUES else None,
        weather=summary.get("weather")
        if summary.get("weather") not in UNKNOWN_VALUES else None,
    )
    for horse in detail.get("horses") or []:
        if not isinstance(horse, dict):
            continue
        no = horse.get("horseNumber")
        if no is None:
            continue
        no = int(no)
        orow = odds_by_no.get(no, {})
        if horse.get("scratched") or orow.get("horse_status"):
            late.scratched[no] = True
        if _present(horse.get("jockey")):
            late.jockey[no] = str(horse["jockey"])
        bw = horse.get("bodyWeight")
        if not _present(bw):
            bw = orow.get("body_weight")
        if _present(bw):
            late.body_weight[no] = float(bw)
        bwc = horse.get("bodyWeightChange")
        if not _present(bwc):
            bwc = orow.get("body_weight_change")
        if _present(bwc):
            late.body_weight_change[no] = float(bwc)
        win_odds = horse.get("winOdds")
        if not _present(win_odds):
            win_odds = orow.get("win_odds")
        if _present(win_odds):
            late.win_odds[no] = float(win_odds)
        pop = horse.get("popularity")
        if not _present(pop):
            pop = orow.get("popularity")
        if _present(pop):
            late.popularity[no] = int(pop)
    return late


def late_inputs_from_snapshot(snapshot: list[dict],
                              condition: Optional[str] = None,
                              weather: Optional[str] = None) -> LateInputs:
    """Rebuild LateInputs from a Phase 0 audit snapshot row list."""
    late = LateInputs(condition=condition, weather=weather)
    for row in snapshot:
        no = row.get("no")
        if no is None:
            continue
        no = int(no)
        if row.get("scratched"):
            late.scratched[no] = True
        if _present(row.get("jockey")):
            late.jockey[no] = str(row["jockey"])
        if _present(row.get("bodyWeight")):
            late.body_weight[no] = float(row["bodyWeight"])
        if _present(row.get("bodyWeightChange")):
            late.body_weight_change[no] = float(row["bodyWeightChange"])
        if _present(row.get("winOdds")):
            late.win_odds[no] = float(row["winOdds"])
        if _present(row.get("popularity")):
            late.popularity[no] = int(row["popularity"])
    return late


def apply_late_inputs(race: RaceRecord, late: LateInputs) -> RaceRecord:
    """Return a new RaceRecord with the late facts folded in.

    Only facts present in ``late`` override the card values; a
    runner the late payload does not mention keeps the card state
    (absence of evidence is not a scratch). Body weight/change and
    win odds are replaced on the runner so downstream consumers see
    the T-30 values with late provenance.
    """
    runners: list[RunnerRecord] = []
    for runner in race.runners:
        n = runner.number
        updated = runner
        if n in late.scratched:
            updated = replace(updated, scratched=True)
        if n in late.jockey:
            updated = replace(updated, jockey=obs(late.jockey[n], LATE_SOURCE))
        if n in late.body_weight:
            updated = replace(
                updated, body_weight=obs(late.body_weight[n], LATE_SOURCE))
        if n in late.body_weight_change:
            updated = replace(
                updated,
                body_weight_change=obs(late.body_weight_change[n], LATE_SOURCE))
        if n in late.win_odds:
            updated = replace(
                updated, win_odds=obs(late.win_odds[n], LATE_SOURCE))
        runners.append(updated)
    return replace(
        race,
        condition=obs(late.condition, LATE_SOURCE)
        if late.condition is not None else race.condition,
        weather=obs(late.weather, LATE_SOURCE)
        if late.weather is not None else race.weather,
        runners=tuple(runners),
    )


def gate_open(summary_path: str | Path) -> tuple[bool, dict]:
    """Phase 0 gate check.

    Returns (open, gate_dict). The lane may seal only when every
    pre-registered gate in the audit summary is literally true;
    a missing or unreadable summary keeps the gate closed.
    """
    try:
        summary = json.loads(Path(summary_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False, {}
    gate = summary.get("gates") or summary.get("gate") or {}
    if not gate:
        return False, {}
    return all(value is True for value in gate.values()), gate
