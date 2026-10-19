"""Stage65 independent, research-only winner/axis challenger.

Never used by Stage64 frozen forecasts or production. No outcomes, odds,
results, post-off data or unsupported performance claims enter this model.
"""
from __future__ import annotations
from math import exp, isfinite
from arvexq.research.stage63.ability import prior_runs, quality
from arvexq.research.stage64.circuits import circuit, discipline, active


def candidates(race: dict, *, expected_circuit: str) -> dict:
    """Create separate win/axis rankings; abstain on insufficient evidence.

    Recent 5 finish quality is a transparent heuristic, NOT a calibrated probability.
    Winner score stresses latest starts; axis score spreads weight across five.
    Exposes individual signals for audit and future independent calibration.
    """
    owner = circuit(race)
    if owner != expected_circuit:
        raise ValueError("cross-circuit execution")
    output = dict(schema="arvexq-stage65-win-focus-research-1", circuit=owner,
                  raceId=race["id"], status="blocked", productionEligible=False,
                  independentlyValidated=False, blockers=[], horses=[],
                  winRole=None, axisRole=None)
    if discipline(race) != "flat":
        output["blockers"].append("unsupported-discipline")
        return output
    horses = race.get("horses")
    if not isinstance(horses, list) or type(race.get("fieldSize")) is not int or len(horses) != race["fieldSize"]:
        raise ValueError("invalid full roster")
    nums = [h.get("horseNumber") for h in horses if isinstance(h, dict)]
    if len(nums) != len(horses) or any(type(n) is not int or n <= 0 for n in nums) or len(set(nums)) != len(nums):
        raise ValueError("invalid horse identity")
    running = [h for h in horses if active(h)]
    if len(running) < 3:
        output["blockers"].append("fewer-than-three-active-runners")
        return output
    for horse in running:
        no = horse["horseNumber"]
        try:
            runs = prior_runs(horse, race["date"])
        except (ValueError, TypeError, AttributeError):
            output["blockers"].append(dict(horseNumber=no, reason="conflicting-history"))
            continue
        runs = [r for r in runs if discipline(r) == "flat"]
        q = [v for r in runs if (v := quality(r)) is not None][:5]
        if not q:
            output["blockers"].append(dict(horseNumber=no, reason="missing-valid-prior-finishes"))
            continue
        # Both candidate ranking rules are intentionally fixed, distinct and interpretable.
        latest_weights = tuple(range(len(q), 0, -1))
        win_score = sum(v*w for v, w in zip(q, latest_weights)) / sum(latest_weights)
        axis_score = sum(q)/len(q)
        if not isfinite(win_score) or not isfinite(axis_score):
            raise ValueError("nonfinite ranking score")
        output["horses"].append(dict(horseNumber=no, sampleRuns=len(q),
                                    winScore=win_score, axisScore=axis_score))
    if output["blockers"]:
        output["status"] = "incomplete-evidence"
        return output
    win = sorted(output["horses"], key=lambda r: (-r["winScore"], -r["sampleRuns"], r["horseNumber"]))
    axis = sorted(output["horses"], key=lambda r: (-r["axisScore"], -r["sampleRuns"], r["horseNumber"]))
    output["horses"] = sorted(output["horses"], key=lambda r:r["horseNumber"])
    output["winRole"] = dict(horseNumber=win[0]["horseNumber"], mark="◎【単】",
                             reason="highest-uncalibrated-recent-form-score")
    output["axisRole"] = dict(horseNumber=axis[0]["horseNumber"], mark="◎【軸】",
                              reason="highest-uncalibrated-five-run-average")
    output["winRanking"] = [r["horseNumber"] for r in win]
    output["axisRanking"] = [r["horseNumber"] for r in axis]
    output["status"] = "research-only-uncalibrated"
    return output
