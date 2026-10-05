from __future__ import annotations

from typing import Any

from arvexq.prediction.ability import rank_ability

MARK_ENGINE_VERSION = "arvexq-ability-record-marks-v3"
CORE_MARKS = ("◎", "○", "▲")
LOWER_MARKS = ("☆+", "☆", "△", "注")


def _n(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _audit(horse: dict[str, Any]) -> dict[str, Any]:
    e = horse.get("integratedEvaluation") or {}
    a = e.get("v218Audit") or e.get("v217Audit") or {}
    return a if isinstance(a, dict) else {}


def _relative_ranks(horses: list[dict[str, Any]], key: str) -> dict[int, int]:
    ordered = sorted(
        horses,
        key=lambda h: (
            -_n(_audit(h).get(key), 0.5),
            int(h.get("horseNumber") or 999),
        ),
    )
    return {id(h): i + 1 for i, h in enumerate(ordered)}


def _plus_candidate(remaining: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Return a rare ☆+ candidate using relative, not fixed percentage, checks.

    ☆+ is allowed only when the best remaining ability/record horse is also near the
    front of at least two race-specific routes (TRUE RUN / scenario / conditions).
    No old P1/P2/P3 score is allowed to replace ◎○▲.
    """
    if len(remaining) < 1:
        return None
    ranks = {
        key: _relative_ranks(remaining, key)
        for key in ("trueRun", "positionScenario", "conditions")
    }
    top_band = max(2, (len(remaining) + 2) // 3)
    for horse in remaining:
        hits = sum(ranks[key].get(id(horse), 999) <= top_band for key in ranks)
        if hits >= 2:
            return horse
    return None


def apply_core_marks(detail: dict[str, Any]) -> dict[str, Any]:
    """Make the displayed marks follow the current ability/record method.

    The legacy evaluator may still calculate auxiliary pace/P2/P3 diagnostics, but it
    can no longer choose or overwrite ◎○▲. Core marks come from `rank_ability()`.
    Race-shape diagnostics are used only to decide whether the best remaining horse
    deserves ☆+; they never replace the top-three ability/record order.
    """
    if not isinstance(detail, dict):
        return detail

    horses = [h for h in (detail.get("horses") or []) if isinstance(h, dict)]
    ranked_rows = rank_ability(horses, detail)
    ranked = [row["horse"] for row in ranked_rows]
    if not ranked:
        return detail

    # Clear every live computed mark first. Pre-race frozen snapshots are separate
    # objects and are intentionally not rewritten here.
    for horse in horses:
        e = horse.setdefault("integratedEvaluation", {})
        e["legacyComputedMark"] = str(e.get("mark") or "")
        e["mark"] = ""
        e["markEngineVersion"] = MARK_ENGINE_VERSION
        e["markSource"] = "ability-record-core"

    detail["abilityRanking"] = []
    for idx, row in enumerate(ranked_rows, 1):
        horse = row["horse"]
        evidence = {
            "rank": idx,
            "score": row["abilityScore"],
            "wins": row["evidenceWins"],
            "weak": row["evidenceWeak"],
            "sample": row["sample"],
            "components": row["components"],
        }
        horse["abilityEvidence"] = evidence
        e = horse.setdefault("integratedEvaluation", {})
        e["coreAbilityRank"] = idx
        e["coreAbilityScore"] = row["abilityScore"]
        e["coreAbilityComponents"] = row["components"]
        detail["abilityRanking"].append(
            {
                "horseNumber": int(horse.get("horseNumber") or 0),
                "name": horse.get("name") or "",
                **evidence,
            }
        )

    # Core marks are deterministic and directly tied to the new prediction method.
    for mark, horse in zip(CORE_MARKS, ranked[:3]):
        horse["integratedEvaluation"]["mark"] = mark

    remaining = ranked[3:]
    used: set[int] = set()
    plus = _plus_candidate(remaining)
    if plus is not None:
        plus["integratedEvaluation"]["mark"] = "☆+"
        used.add(id(plus))

    leftovers = [h for h in remaining if id(h) not in used]
    for mark, horse in zip(("☆", "△", "注"), leftovers[:3]):
        horse["integratedEvaluation"]["mark"] = mark

    # Display/order metadata must describe the same method that produced the marks.
    mark_order = {"◎": 1, "○": 2, "▲": 3, "☆+": 4, "☆": 5, "△": 6, "注": 7}
    marked = sorted(
        ranked,
        key=lambda h: (
            mark_order.get(str((h.get("integratedEvaluation") or {}).get("mark") or ""), 99),
            int((h.get("integratedEvaluation") or {}).get("coreAbilityRank") or 999),
            int(h.get("horseNumber") or 999),
        ),
    )
    for idx, horse in enumerate(marked, 1):
        horse["integratedEvaluation"]["rank"] = idx

    detail["markEngineVersion"] = MARK_ENGINE_VERSION
    detail["markMethod"] = "ability-record-core; pace only lower-mark tie/uplift"
    return detail
