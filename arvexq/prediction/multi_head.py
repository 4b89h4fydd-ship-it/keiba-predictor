from __future__ import annotations

from statistics import median
from typing import Any

MODEL_VERSION = "arvexq-multi-head-v1"


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
    """Attach separate, race-relative decision heads without inventing probabilities.

    strength: ability + record only.
    win: all four primary pillars.
    upside: suitability + pace + support; used to find horses whose current setup
      can outperform their baseline or market rank.
    fragility: disagreement among the four primary pillars. This is an index of
      instability, not a loss probability.
    market disagreement: compares pre-race popularity rank with the model ranks.
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
            "popularityRank": popularity or None,
            "marketGap": market_gap,
            # High market rank but the model puts the horse materially lower.
            "dangerPopular": bool(popularity and popularity <= 3 and win_rank >= popularity + 2),
            # Lower market attention while win/setup heads both keep the horse live.
            "upsideCandidate": bool(popularity and popularity >= 5 and win_rank <= 4 and upside_rank <= 3),
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
