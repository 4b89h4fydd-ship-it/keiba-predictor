"""Independent evidence for ☆ (pace reversal) and 注 (overlooked form).

This is a mark *allocation* layer, not a replacement for JRA/NAR scoring.
Only dated pre-race observations are considered, with no odds, result leakage,
neutral score substitutions or mandatory special marks.
"""
from __future__ import annotations

from math import ceil, isfinite
from typing import Any

from arvexq.prediction.past_performance import observed_runs


def _num(value: Any) -> float | None:
    try:
        value = float(value)
        return value if isfinite(value) else None
    except (ValueError, TypeError):
        return None


def _corners(run: dict[str, Any]) -> list[int]:
    raw = run.get("cornerPositions") or []
    if not isinstance(raw, list):
        return []
    return [int(v) for v in raw if _num(v) is not None and _num(v) >= 1]


def _histories(rows: list[dict[str, Any]], race: dict[str, Any]
               ) -> tuple[dict[int, list[dict[str, Any]]], int]:
    histories: dict[int, list[dict[str, Any]]] = {}
    front = 0
    for row in rows:
        horse = row["horse"]
        no = int(horse.get("horseNumber") or 0)
        runs = observed_runs(horse, race, limit=5)
        histories[no] = runs
        # Race-level pace pressure: other runners with an observed early lead
        # in any of their three latest valid starts. No invented sectional time.
        if any((_corners(run) or [999])[0] <= 3 for run in runs[:3]):
            front += 1
    return histories, front


def _evidence(runs: list[dict[str, Any]], race: dict[str, Any],
              front: int) -> dict[str, Any]:
    advancing: list[float] = []
    podium = 0
    same = False
    class_top3 = False
    close_margin = False
    earlier_peak = False
    distance = _num(race.get("distance"))
    for idx, run in enumerate(runs):
        finish = _num(run.get("finish"))
        field = _num(run.get("fieldSize"))
        if finish is None or field is None or field < 2 or not 1 <= finish <= field:
            continue
        if finish <= 3:
            podium += 1
        corners = _corners(run)
        if corners and 1 <= corners[-1] <= field and corners[-1] - finish >= 2 and finish <= ceil(field / 2):
            advancing.append((corners[-1] - finish) / (field - 1))
        margin = next((_num(run.get(k)) for k in ("marginSeconds", "timeBehindWinner")
                       if _num(run.get(k)) is not None), None)
        if margin is not None and 0 <= margin <= .70 and finish > 2:
            close_margin = True
        run_distance = _num(run.get("distance"))
        if (finish <= 3 and distance is not None and run_distance is not None
                and abs(run_distance - distance) <= 150
                and run.get("track") and run.get("track") == race.get("track")
                and run.get("surface") and run.get("surface") == race.get("surface")):
            same = True
        level = _num(run.get("opponentLevel"))
        if finish <= 3 and level is not None and .65 <= level <= 1:
            class_top3 = True
        if idx > 0 and finish <= 3 and runs and _num(runs[0].get("finish")) is not None and _num(runs[0]["finish"]) >= 4:
            earlier_peak = True
    # ☆ needs both an observed finishing gain and a plausible pace-collapse
    # setting. It is not a fifth-place award or general factor-score gate.
    star_ok = len(runs) >= 2 and front >= 3 and bool(advancing) and podium >= 1
    star_strength = (.50 * min(1., max(advancing, default=0.) * 3)
                     + .30 * min(1., len(advancing) / 2)
                     + .20 * min(1., front / 5)) if star_ok else 0.
    flags = [label for label, present in (
        ("close-margin", close_margin), ("same-course-distance-podium", same),
        ("strong-opposition-podium", class_top3), ("earlier-peak", earlier_peak)
    ) if present]
    # Two independent forms of proof, including at least one actual podium,
    # prevent 注 from becoming a catch-all for any poor recent finisher.
    note_ok = len(runs) >= 2 and podium >= 1 and len(flags) >= 2
    note_strength = (.40 + .15 * min(4, len(flags))
                     + .05 * min(2, podium)) if note_ok else 0.
    return {"star": bool(star_ok), "note": bool(note_ok),
            "starStrength": round(star_strength, 6),
            "noteStrength": round(note_strength, 6),
            "frontPressureRunners": front, "closingGainRuns": len(advancing),
            "podiumRuns": podium, "noteReasons": flags}


def allocate_special_marks(ranked: list[dict[str, Any]], race: dict[str, Any]
                           ) -> dict[int, dict[str, Any]]:
    """Keep ◎ and ○; compare competing ☆/注 evidence for all other runners.

    Strong independent evidence may supersede an ordinary ▲/△. Remaining core
    roles move to the next highest main-model runner, with no duplicate marks.
    """
    histories, front = _histories(ranked, race)
    evidence: dict[int, dict[str, Any]] = {}
    proposals: list[tuple[float, int, int, str]] = []
    for idx, row in enumerate(ranked):
        horse = row["horse"]
        no = int(horse.get("horseNumber") or 0)
        e = _evidence(histories.get(no, []), race, front)
        evidence[no] = e
        if idx < 2:
            continue  # Preserve the two primary win roles.
        if e["star"]:
            proposals.append((-e["starStrength"], idx, no, "☆"))
        if e["note"]:
            proposals.append((-e["noteStrength"], idx, no, "注"))
    selected: dict[int, str] = {}
    used_roles: set[str] = set()
    for _, _, no, mark in sorted(proposals):
        if no not in selected and mark not in used_roles:
            selected[no] = mark
            used_roles.add(mark)
    for idx, row in enumerate(ranked):
        no = int(row["horse"].get("horseNumber") or 0)
        if idx == 0:
            mark = "◎"
        elif idx == 1:
            mark = "○"
        else:
            mark = selected.get(no, "")
        evidence[no]["mark"] = mark
    # Give ○ its existing win-contender role. Choose ▲ for expected second/third
    # and △ for third-place propensity, rather than reusing overall rank order.
    import math
    available = [row for row in ranked[2:] if not evidence[int(row["horse"]["horseNumber"])]["mark"]]
    if available:
        strengths = [math.exp((float(row["score"]) - float(ranked[0]["score"])) / .15) for row in ranked]
        total = sum(strengths)
        p2, p3 = [0.] * len(ranked), [0.] * len(ranked)
        if total > 0:
            for i, wi in enumerate(strengths):
                other = total - wi
                if other <= 0: continue
                for j, wj in enumerate(strengths):
                    if i == j: continue
                    second = wi / total * wj / other
                    p2[j] += second
                    left = other - wj
                    if left > 0:
                        for k, wk in enumerate(strengths):
                            if k != i and k != j: p3[k] += second * wk / left
        idx = {int(row["horse"]["horseNumber"]): i for i, row in enumerate(ranked)}
        triangle = max(available, key=lambda row: (p2[idx[int(row["horse"]["horseNumber"])]] + p3[idx[int(row["horse"]["horseNumber"])]], -int(row["horse"]["horseNumber"])))
        triangle_no = int(triangle["horse"]["horseNumber"])
        evidence[triangle_no]["mark"] = "▲"
        rest = [row for row in available if int(row["horse"]["horseNumber"]) != triangle_no]
        if rest:
            delta = max(rest, key=lambda row: (p3[idx[int(row["horse"]["horseNumber"])]], -int(row["horse"]["horseNumber"])))
            evidence[int(delta["horse"]["horseNumber"])]["mark"] = "△"
    return evidence
