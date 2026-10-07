from __future__ import annotations

from typing import Any

GATE_VERSION = "arvexq-honmei-consensus-gate-v2"
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
    race: dict[str, Any] | None = None,
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
    ability_families = _iv(family_counts.get("ability"))
    record_families = _iv(family_counts.get("record"))
    suitability_families = _iv(family_counts.get("suitability"))
    pace_families = _iv(family_counts.get("pace"))
    circuit = str((race or {}).get("circuit") or "")
    central = circuit in {"中央", "JRA"}
    prepared = (race or {}).get("preparedMeta") if isinstance((race or {}).get("preparedMeta"), dict) else {}
    supplemental = prepared.get("supplementalSearch") if isinstance(prepared.get("supplementalSearch"), dict) else {}
    central_supplemented = supplemental.get("version") == "arvexq-multi-source-fallback-v1"
    history = horse.get("recentRaces") or horse.get("allPastRuns") or []
    central_complete_runs = 0
    for run in history[:5]:
        if not isinstance(run, dict):
            continue
        try:
            finish = int(float(run.get("finish") or run.get("finishPosition") or run.get("rank") or 0))
            field = int(float(run.get("fieldSize") or 0))
            seconds = float(run.get("timeSeconds") or 0)
            distance = int(float(run.get("distance") or 0))
        except (TypeError, ValueError):
            continue
        if finish > 0 and field > 1 and seconds > 0 and distance > 0:
            central_complete_runs += 1

    win_gap = _fv(summary.get("winnerGap"))
    pairwise_wins = _iv(leader.get("pairwiseWins"))
    runner_pairwise_wins = _iv((runner or {}).get("pairwiseWins"))

    checks = {
        "coreWinHeadAgreement": (
            _iv(summary.get("winnerHorseNumber")) == horse_no
            and _iv(multi.get("winRank"), 999) == 1
        ),
        # 7-day replay + held-out final two days: rank-1 baseline strength and
        # all four pillars in the top 3 were materially more stable than the
        # previous <=2 / 3-of-4 gate.
        "strengthHeadSupport": _iv(multi.get("strengthRank"), 999) == 1,
        "allPrimaryPillarsPresent": primary_coverage >= 4,
        "pillarConsensus": pillar_top3 >= 4,
        "positiveWinHeadGap": win_gap is not None and win_gap > 0.0,
        "pairwiseSeparation": runner is None or pairwise_wins > runner_pairwise_wins,
        "minimumRaceEvidence": sample >= 5 and primary_families >= 8 and pace_families >= 1,
    }
    if central:
        # Historical JRA audit showed thin evidence (missing class/sectional/complete
        # recent-run fields) produced false confidence. Central ◎ automatically
        # resumes only when the richer evidence families are actually present.
        checks.update({
            "centralSupplemented": central_supplemented,
            "centralFiveRunsComplete": central_complete_runs >= 5,
            "centralAbilityDepth": ability_families >= 3,
            "centralRecordDepth": record_families >= 4,
            "centralSuitabilityDepth": suitability_families >= 2,
            "centralPaceDepth": pace_families >= 2,
            "centralEvidenceDepth": primary_families >= 11,
        })
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
        "evidenceFamilies": {
            "ability": ability_families,
            "record": record_families,
            "suitability": suitability_families,
            "pace": pace_families,
        },
        "circuit": circuit,
        "centralEvidenceGate": central,
        "centralSupplemented": central_supplemented,
        "centralCompleteRuns": central_complete_runs,
        "sample": sample,
    }
