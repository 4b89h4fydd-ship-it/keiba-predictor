from __future__ import annotations

from typing import Any

GATE_VERSION = "arvexq-honmei-consensus-gate-v1"
PRIMARY_PILLARS = ("ability", "record", "suitability", "pace")


def _iv(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _fv(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if out == out else None


def evaluate_honmei_gate(
    ranked_rows: list[dict[str, Any]],
    multi_head_summary: dict[str, Any] | None,
) -> dict[str, Any]:
    """Decide whether ARVEXQ is allowed to publish an ◎.

    This is intentionally a structural-consensus gate, not a fabricated win
    probability. A race may still have a top-ranked horse while ◎ is withheld.
    That is preferable to presenting weak separation as a strong honmei call.
    """
    if not ranked_rows:
        return {
            "version": GATE_VERSION,
            "eligible": False,
            "horseNumber": 0,
            "reason": "ranking-unavailable",
            "failed": ["ranking"],
        }

    leader = ranked_rows[0]
    runner = ranked_rows[1] if len(ranked_rows) > 1 else None
    horse = leader.get("horse") or {}
    horse_no = _iv(horse.get("horseNumber"))
    multi = leader.get("multiHead") or {}
    summary = multi_head_summary or {}

    pillar_ranks = leader.get("pillarRanks") or {}
    pillar_top3 = sum(_iv(pillar_ranks.get(p), 999) <= 3 for p in PRIMARY_PILLARS)
    primary_coverage = _iv(leader.get("primaryPillarCoverage"))
    sample = _iv(leader.get("sample"))
    family_counts = leader.get("evidenceFamilyCounts") or {}
    primary_families = sum(_iv(family_counts.get(p)) for p in PRIMARY_PILLARS)

    win_gap = _fv(summary.get("winnerGap"))
    pairwise_wins = _iv(leader.get("pairwiseWins"))
    runner_pairwise_wins = _iv((runner or {}).get("pairwiseWins"))

    checks = {
        "coreWinHeadAgreement": (
            _iv(summary.get("winnerHorseNumber")) == horse_no
            and _iv(multi.get("winRank"), 999) == 1
        ),
        "strengthHeadSupport": _iv(multi.get("strengthRank"), 999) <= 2,
        "allPrimaryPillarsPresent": primary_coverage >= 4,
        "pillarConsensus": pillar_top3 >= 3,
        "positiveWinHeadGap": win_gap is not None and win_gap > 0.0,
        "pairwiseSeparation": runner is None or pairwise_wins > runner_pairwise_wins,
        "minimumRaceEvidence": sample >= 2 and primary_families >= 4,
    }
    failed = [name for name, ok in checks.items() if not ok]
    eligible = not failed

    return {
        "version": GATE_VERSION,
        "eligible": eligible,
        "horseNumber": horse_no,
        "reason": "honmei-consensus-passed" if eligible else "honmei-withheld",
        "failed": failed,
        "checks": checks,
        "winHeadGap": win_gap,
        "pairwiseWins": pairwise_wins,
        "runnerPairwiseWins": runner_pairwise_wins,
        "primaryPillarCoverage": primary_coverage,
        "pillarTop3Count": pillar_top3,
        "primaryEvidenceFamilies": primary_families,
        "sample": sample,
    }
