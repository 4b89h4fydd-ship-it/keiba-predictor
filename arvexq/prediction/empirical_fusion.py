"""Empirical Mineta-led, multi-expert, multi-AI decision calculus.

Research component for the EXISTING forecast path, not a data collection route.
Never silently substitute invented expert votes, AI estimates, odds, or weights.
The captured-at clock and strictly earlier evaluation races are mandatory.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, date
from itertools import combinations, permutations
from math import isfinite
from typing import Mapping

VERSION = "arvexq-empirical-fusion-v1"
MARKS = ("◎", "○", "▲", "△", "☆")
BET_TYPES = {"馬連": 2, "ワイド": 2, "馬単": 2, "3連複": 3, "3連単": 3}


def _timestamp(value):
    if not isinstance(value, str):
        raise ValueError("timestamp required")
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise ValueError("timezone-aware timestamp required")
    return stamp


def _number(value):
    if type(value) not in (int, float) or not isfinite(value):
        raise ValueError("finite numeric observation required")
    return float(value)


def _probs(source, roster, *, three=False):
    if not isinstance(source, dict):
        raise ValueError("explicit probability map required")
    expected = {str(no) for no in roster}
    if set(str(k) for k in source) != expected:
        raise ValueError("probabilities must cover identical active roster")
    clean = {int(k): _number(v) for k, v in source.items()}
    if any(v < 0 or v > 1 for v in clean.values()):
        raise ValueError("invalid probability")
    if abs(sum(clean.values()) - (3 if three else 1)) > 1e-5:
        raise ValueError("probability mass must be normalized before integration")
    return clean


def _arms(arms):
    if not isinstance(arms, dict):
        raise ValueError("five independently recorded method outputs required")
    names = set(arms)
    experts = {k for k in names if k.startswith("expert:")}
    ais = {k for k in names if k.startswith("ai:")}
    if "mineta" not in names or len(experts) < 2 or len(ais) < 2 or len(names) != 1 + len(experts) + len(ais):
        raise ValueError("Mineta, at least two independent experts and two independent AIs required")
    if any(not isinstance(v, dict) for v in arms.values()):
        raise ValueError("each method must provide its own observed forecast")
    return names


def _validate_opinion_sources(arms, scheduled_off, race_id):
    """Reject reused method identities and post-off individual predictions."""
    versions = set()
    for name, opinion in arms.items():
        version = str(opinion.get("modelVersion") or "")
        evidence_id = str(opinion.get("evidenceId") or "")
        if not version or not evidence_id or opinion.get("raceId") != race_id:
            raise ValueError("independent method identity/evidence missing")
        if version in versions:
            raise ValueError("duplicate model identity disguised as independent methods")
        versions.add(version)
        if _timestamp(opinion.get("capturedAt")) >= _timestamp(scheduled_off):
            raise ValueError("post-off method opinion is not preoff evidence")


def _validate_capture(row, cutoff):
    race_day = date.fromisoformat(str(row["raceDate"]))
    if race_day >= date.fromisoformat(cutoff):
        raise ValueError("training must predate the target race")
    if _timestamp(row["capturedAt"]) >= _timestamp(row["scheduledOffAt"]):
        raise ValueError("post-off labels cannot be promoted to pre-off opinions")
    if not str(row.get("raceId") or ""):
        raise ValueError("race identity required")
    return race_day


def fit_weights(history, *, target_date, min_races=30):
    """Fit on matched, immutable, PRE-target evaluations only.

    A method's empirically observed winner-hit frequency and actual return
    multiple are the entire weight formula: no subjective votes/hand-tuning.
    Every method is scored against exactly the same race cohort.
    Historical stake and return MUST be sourced from frozen tickets and payouts.
    """
    if type(min_races) is not int or min_races < 1:
        raise ValueError("positive minimum race sample required")
    if not isinstance(history, list) or len(history) < min_races:
        raise ValueError("insufficient independently scored races")
    seen = set()
    stats = defaultdict(lambda: {"wins": 0, "stake": 0., "returned": 0., "races": 0})
    names = None
    versions = None
    circuits = set()
    for row in history:
        _validate_capture(row, target_date)
        key = (row["raceDate"], row["raceId"])
        if key in seen:
            raise ValueError("duplicate evaluation race")
        seen.add(key)
        circuits.add(str(row.get("circuit") or ""))
        current = _arms(row["arms"])
        _validate_opinion_sources(row["arms"], row["scheduledOffAt"], row["raceId"])
        current_versions = {name: data["modelVersion"] for name, data in row["arms"].items()}
        if versions is None:
            versions = current_versions
        elif versions != current_versions:
            raise ValueError("evaluation model versions changed across cohort")
        if names is None:
            names = current
        if names != current:
            raise ValueError("all methods must be evaluated on the same races")
        if not isinstance(row.get("finishers"), list) or len(row["finishers"]) < 3:
            raise ValueError("verified actual finish order is required")
        finish = row["finishers"]
        if len(set(finish)) != len(finish) or any(type(n) is not int or n < 1 for n in finish):
            raise ValueError("invalid actual finish order")
        roster = list(row.get("roster") or [])
        if len(roster) < 5 or len(set(roster)) != len(roster) or not set(finish).issubset(roster):
            raise ValueError("complete consistent preoff roster required")
        for method, opinion in row["arms"].items():
            scores = _probs(opinion.get("win"), roster)
            _probs(opinion.get("top3"), roster, three=True)
            if not opinion.get("evidenceId") or not opinion.get("modelVersion"):
                raise ValueError("each independent method needs a traceable version and evidence ID")
            stake, returned = _number(opinion.get("stakeYen")), _number(opinion.get("returnYen"))
            if stake <= 0 or returned < 0:
                raise ValueError("frozen stake and actual return needed for ROI weights")
            s = stats[method]
            s["races"] += 1
            s["wins"] += int(max(scores, key=lambda n: (scores[n], -n)) == finish[0])
            s["stake"] += stake
            s["returned"] += returned
    if len(circuits) != 1 or circuits == {""}:
        raise ValueError("JRA and NAR must be fitted separately")
    raw = {k: (v["wins"] / v["races"]) * (v["returned"] / v["stake"]) for k, v in stats.items()}
    mass = sum(raw.values())
    if mass <= 0:
        raise ValueError("no empirically supported positive weighting")
    return {
        "version": VERSION, "trainedThrough": max(row["raceDate"] for row in history),
        "targetDate": target_date, "circuit": next(iter(circuits)),
        "evaluatedRaceIds": sorted(seen), "nRaces": len(seen),
        "methodVersions": dict(sorted(versions.items())),
        "weights": {k: raw[k] / mass for k in sorted(raw)},
        "metrics": {k: {"winHits": v["wins"], "races": v["races"],
                         "winHitRate": v["wins"] / v["races"],
                         "stakeYen": v["stake"], "returnYen": v["returned"],
                         "roi": v["returned"] / v["stake"]} for k, v in sorted(stats.items())},
        "formula": "weight proportional to observed winner hit rate times realized ROI",
        "weightsIndependentOfTargetOutcome": True,
    }


def _joint(opinion, roster):
    rows = opinion.get("trifecta")
    if not isinstance(rows, list) or not rows:
        return None
    mapped = {}
    for row in rows:
        combo = row.get("combo")
        if (not isinstance(combo, list) or len(combo) != 3
                or any(type(n) is not int or n not in roster for n in combo)
                or len(set(combo)) != 3):
            raise ValueError("invalid finishing-order outcome")
        key = tuple(combo)
        if key in mapped:
            raise ValueError("duplicate finishing-order outcome")
        mapped[key] = _number(row.get("probability"))
        if mapped[key] < 0:
            raise ValueError("negative finishing-order probability")
    if abs(sum(mapped.values()) - 1) > 1e-5:
        raise ValueError("unnormalized finishing-order model")
    return mapped


def _hit(kind, combo, finish):
    if kind == "馬単":
        return tuple(finish[:2]) == combo
    if kind == "馬連":
        return set(finish[:2]) == set(combo)
    if kind == "ワイド":
        return set(combo).issubset(finish[:3])
    if kind == "3連複":
        return set(combo) == set(finish[:3])
    if kind == "3連単":
        return combo == finish[:3]
    raise ValueError("unsupported betting kind")


def _quoted_prices(quotes):
    """Accept a portable JSON quote list, never a fabricated tuple-key map."""
    if not isinstance(quotes, dict):
        raise ValueError("timestamped official quote envelope required")
    if quotes.get("sourceKind") != "official_preoff_quotes":
        raise ValueError("official preoff ticket-price source required")
    rows = quotes.get("prices")
    if isinstance(rows, dict):
        # In-process tools can supply tuple keys. External JSON transport uses
        # the structured list variant below.
        return rows
    if not isinstance(rows, list):
        raise ValueError("structured official prices required")
    out = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("invalid official price record")
        kind, combo = row.get("kind"), row.get("combo")
        if (kind not in BET_TYPES or not isinstance(combo, list) or
                len(combo) != BET_TYPES[kind] or
                any(type(n) is not int or n < 1 for n in combo) or
                len(set(combo)) != len(combo)):
            raise ValueError("invalid official quote combination")
        if kind in ("馬連", "ワイド", "3連複"):
            combo = sorted(combo)
        key = (kind, tuple(combo))
        if key in out:
            raise ValueError("duplicate official quote combination")
        out[key] = _number(row.get("odds"))
    return out


def _tickets(joint, marks, quoted_odds, limit):
    if joint is None or not isinstance(quoted_odds, dict):
        return [], "joint-distribution-or-verified-odds-unavailable"
    candidates = []
    horses = [m["horseNumber"] for m in marks]
    for kind, length in BET_TYPES.items():
        combos = permutations(horses, length) if kind in {"馬単", "3連単"} else combinations(horses, length)
        for combo in combos:
            quote = quoted_odds.get((kind, tuple(combo)))
            if quote is None:
                continue
            odds = _number(quote)
            if odds <= 1:
                continue
            events = frozenset(finish for finish in joint if _hit(kind, combo, finish))
            p = sum(joint[x] for x in events)
            ev = p * odds
            if p > 0 and ev >= 1:
                candidates.append((kind, tuple(combo), p, odds, ev, events))
    selected, covered = [], set()
    while candidates and len(selected) < limit:
        # Primary: new portfolio hit coverage; secondary: ticket expectation.
        best = min(candidates, key=lambda c: (
            -sum(joint[x] for x in c[5] - covered), -c[4], c[0], c[1]))
        gain = sum(joint[x] for x in best[5] - covered)
        if gain <= 0:
            break
        selected.append({"kind": best[0], "combo": list(best[1]),
                         "hitProbability": best[2], "quotedOdds": best[3],
                         "expectedReturn": best[4]})
        covered.update(best[5])
        candidates.remove(best)
    return selected, ("empirical-joint-and-quoted-odds" if selected else "no-positive-expectation-tickets")


def blend(race, opinions, fitted, *, quoted_odds=None, max_tickets=5):
    """Use recorded individual methods and fitted weights, never human overrides."""
    if not isinstance(race, dict) or not isinstance(fitted, dict) or fitted.get("version") != VERSION:
        raise ValueError("verified learned weights required")
    today = str(race["date"])
    if fitted.get("targetDate") != today:
        raise ValueError("empirical calibration is not for this exact target date")
    if date.fromisoformat(fitted["trainedThrough"]) >= date.fromisoformat(today):
        raise ValueError("training date must precede prediction date")
    if fitted["circuit"] != race.get("circuit"):
        raise ValueError("separate JRA and NAR model calibration required")
    if not isinstance(max_tickets, int) or not 1 <= max_tickets <= 5:
        raise ValueError("maximum five total tickets")
    methods = _arms(opinions)
    from zoneinfo import ZoneInfo
    try:
        off_clock = str(race.get("scheduledStartTime") or race.get("startTime") or "")
        if len(off_clock) < 5:
            raise ValueError("scheduled race off required")
        scheduled_off = datetime.fromisoformat(today + "T" + off_clock[:5] + ":00").replace(
            tzinfo=ZoneInfo("Asia/Tokyo")).isoformat()
    except (ValueError, TypeError) as exc:
        raise ValueError("verified scheduled race off required") from exc
    _validate_opinion_sources(opinions, scheduled_off, race["id"])
    weights = fitted.get("weights")
    if (fitted.get("nRaces", 0) < 30 or
            len(fitted.get("evaluatedRaceIds") or []) != fitted.get("nRaces") or
            fitted.get("weightsIndependentOfTargetOutcome") is not True):
        raise ValueError("insufficient verified empirical calibration sample")
    if fitted.get("methodVersions") != {
            name: value["modelVersion"] for name, value in opinions.items()}:
        raise ValueError("active method versions differ from backtested cohort")
    if not isinstance(weights, dict) or methods != set(weights) or abs(sum(weights.values()) - 1.) > 1e-7:
        raise ValueError("fitted method/weight mismatch")
    if any(type(w) not in (float, int) or not isfinite(w) or w < 0 for w in weights.values()):
        raise ValueError("invalid fitted method weight")
    active = [h for h in race.get("horses", []) if not (
        h.get("scratched") or h.get("withdrawn") or h.get("cancelled"))]
    roster = [h["horseNumber"] for h in active]
    if len(roster) < 5 or len(set(roster)) != len(roster):
        raise ValueError("valid complete active field required")
    win, top3 = defaultdict(float), defaultdict(float)
    joint = defaultdict(float)
    all_joint = True
    for method, opinion in opinions.items():
        if not opinion.get("evidenceId") or not opinion.get("modelVersion"):
            raise ValueError("unverified independent opinion")
        p1 = _probs(opinion.get("win"), roster)
        p3 = _probs(opinion.get("top3"), roster, three=True)
        for no in roster:
            win[no] += weights[method] * p1[no]
            top3[no] += weights[method] * p3[no]
        j = _joint(opinion, roster)
        if j is None:
            all_joint = False
        else:
            for finish, value in j.items():
                joint[finish] += weights[method] * value
    ranked = sorted(roster, key=lambda no: (-win[no], -top3[no], no))
    marks = [{"horseNumber": no, "mark": mark, "winProbability": win[no],
              "top3Probability": top3[no]} for no, mark in zip(ranked, MARKS)]
    verified_odds = None
    if quoted_odds is not None:
        if not isinstance(quoted_odds, dict) or not isinstance(quoted_odds.get("prices"), (dict, list)):
            raise ValueError("timestamped official odds quotes required")
        if _timestamp(quoted_odds.get("capturedAt")) >= _timestamp(scheduled_off):
            raise ValueError("post-off odds cannot determine a preoff ticket")
        verified_odds = _quoted_prices(quoted_odds)
    tickets, ticket_status = _tickets(joint if all_joint else None, marks, verified_odds, max_tickets)
    return {
        "version": VERSION, "circuit": race["circuit"], "raceId": race["id"],
        "predictionDate": today, "methodWeights": dict(sorted(weights.items())),
        "methodEvidence": {name: {"evidenceId": o["evidenceId"],
                                   "modelVersion": o["modelVersion"]} for name, o in sorted(opinions.items())},
        "win": dict(win), "top3": dict(top3), "predictionMarks": marks,
        "recommendedBets": tickets, "betStatus": ticket_status,
        "source": "independent-preoff-methods-with-empirical-history-only",
        "calibrationRaces": fitted["nRaces"], "humanOverrideAllowed": False,
    }
