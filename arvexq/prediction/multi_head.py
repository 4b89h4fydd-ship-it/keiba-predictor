from __future__ import annotations

from statistics import median
from typing import Any

MODEL_VERSION = "arvexq-multi-head-v2"


def _median(values: list[float | None]) -> float | None:
    available = [float(v) for v in values if v is not None]
    return float(median(available)) if available else None


def _rank_rows(rows: list[dict[str, Any]], key: str) -> dict[int, int]:
    values = sorted({float(row[key]) for row in rows if row.get(key) is not None}, reverse=True)
    by_value = {value: idx + 1 for idx, value in enumerate(values)}
    missing = len(values) + 1
    return {
        id(row): by_value.get(float(row[key]), missing) if row.get(key) is not None else missing
        for row in rows
    }


def attach_multi_head_signals(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Attach separate race-relative decision heads without inventing probabilities.

    Core heads remain market independent:
      strength = ability + record
      win = ability + record + suitability + pace
      upside = suitability + pace + support
      fragility = disagreement among primary pillars

    Popularity disagreement is stored only as a market diagnostic. It must not alter
    the core ranking, ☆+ eligibility, or strict selection gate.
    """
    if not rows:
        return {"modelVersion": MODEL_VERSION, "winnerGap": None, "winnerHorseNumber": 0}

    for row in rows:
        ability = row.get("ability")
        record = row.get("record")
        suitability = row.get("suitability")
        pace = row.get("pace")
        support = row.get("support")
        primary = [ability, record, suitability, pace]
        present = [float(v) for v in primary if v is not None]

        row["strengthHeadScore"] = _median([ability, record])
        row["winHeadScore"] = _median(primary)
        row["upsideHeadScore"] = _median([suitability, pace, support])
        row["fragilityHeadScore"] = (max(present) - min(present)) if len(present) >= 2 else None

    strength_ranks = _rank_rows(rows, "strengthHeadScore")
    win_ranks = _rank_rows(rows, "winHeadScore")
    upside_ranks = _rank_rows(rows, "upsideHeadScore")
    fragility_ranks = _rank_rows(rows, "fragilityHeadScore")

    for row in rows:
        horse = row.get("horse") or {}
        popularity = int(horse.get("popularity") or 0)
        strength_rank = strength_ranks[id(row)]
        win_rank = win_ranks[id(row)]
        upside_rank = upside_ranks[id(row)]
        fragility_rank = fragility_ranks[id(row)]

        market_gap = popularity - win_rank if popularity > 0 else None
        # Upside is a pure racing/setup signal: current suitability/pace/support lift
        # the horse above its baseline strength rank. Popularity is deliberately absent.
        setup_lift = strength_rank - win_rank
        upside_candidate = bool(win_rank <= 4 and upside_rank <= 3 and setup_lift >= 1)

        row["multiHead"] = {
            "modelVersion": MODEL_VERSION,
            "strengthScore": row.get("strengthHeadScore"),
            "strengthRank": strength_rank,
            "winScore": row.get("winHeadScore"),
            "winRank": win_rank,
            "upsideScore": row.get("upsideHeadScore"),
            "upsideRank": upside_rank,
            "fragilityScore": row.get("fragilityHeadScore"),
            "fragilityRank": fragility_rank,
            "setupLift": setup_lift,
            "upsideCandidate": upside_candidate,
            # Market diagnostics are metadata only; they never drive core marks.
            "popularityRank": popularity or None,
            "marketGap": market_gap,
            "dangerPopular": bool(popularity and popularity <= 3 and win_rank >= popularity + 2),
        }

    ranked = sorted(
        rows,
        key=lambda row: (
            win_ranks[id(row)],
            strength_ranks[id(row)],
            upside_ranks[id(row)],
            int((row.get("horse") or {}).get("horseNumber") or 999),
        ),
    )
    leader = ranked[0]
    second = ranked[1] if len(ranked) > 1 else None
    leader_score = leader.get("winHeadScore")
    second_score = second.get("winHeadScore") if second else None
    gap = None
    if leader_score is not None and second_score is not None:
        gap = float(leader_score) - float(second_score)

    return {
        "modelVersion": MODEL_VERSION,
        "winnerHorseNumber": int((leader.get("horse") or {}).get("horseNumber") or 0),
        "winnerGap": gap,
        "winnerScore": leader_score,
        "secondScore": second_score,
        "ranking": [
            {
                "horseNumber": int((row.get("horse") or {}).get("horseNumber") or 0),
                **row["multiHead"],
            }
            for row in ranked
        ],
    }
