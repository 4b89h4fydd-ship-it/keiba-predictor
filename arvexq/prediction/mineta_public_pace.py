"""Observable public Mineta-method pace factors, NOT his proprietary forecast.

Read only official pre-off race geometry and the existing observed-runs lane.
Do not convert these cues into fabricated win odds. Fit effects on independently
scored earlier races through the empirical fusion contract instead.
"""
from __future__ import annotations

from math import isfinite
from urllib.parse import urlsplit

from arvexq.prediction.past_performance import observed_runs

VERSION = "arvexq-mineta-public-pace-evidence-v1"
OFFICIAL_HOSTS = frozenset({
    "jra.go.jp", "www.jra.go.jp", "www.keiba.go.jp", "keiba.go.jp",
    "www.keiba.or.jp", "www.tokyocitykeiba.com", "www.sonoda-himeji.jp",
    "www.kawasaki-keiba.jp", "www.nagoyakeiba.com", "www.sagakeiba.net"
})


def _finite(value):
    if type(value) not in (int, float) or not isfinite(value):
        return None
    return float(value)


def _verified_first_corner(race):
    record = race.get("courseGeometry")
    if not isinstance(record, dict):
        return None
    url = urlsplit(str(record.get("sourceUrl") or ""))
    distance = _finite(record.get("firstCornerDistanceMeters"))
    race_distance = _finite(race.get("distance"))
    geometry_distance = _finite(record.get("distance"))
    if (record.get("sourceKind") != "official_course_geometry"
            or record.get("sourcePublishedBeforeOff") is not True
            or url.scheme != "https" or url.hostname not in OFFICIAL_HOSTS
            or str(record.get("track") or "") != str(race.get("track") or "")
            or record.get("surface") != race.get("surface")
            or distance is None or not 0 < distance < 5000
            or race_distance is None or race_distance != geometry_distance):
        return None
    # Date/time chronology of official course geometry is checked by the
    # acquisition stage. Never accept a same-day post-off source as pre-off.
    stamp = record.get("publishedAt")
    if not isinstance(stamp, str):
        return None
    from datetime import datetime
    from zoneinfo import ZoneInfo
    try:
        published = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        off = datetime.fromisoformat(
            str(race["date"]) + "T" + str(race.get("scheduledStartTime")
                 or race.get("startTime"))[:5] + ":00").replace(
                     tzinfo=ZoneInfo("Asia/Tokyo"))
        if published.tzinfo is None or published >= off:
            return None
    except (ValueError, TypeError, KeyError):
        return None
    return distance


def _positions(run):
    raw = run.get("cornerPositions") or run.get("passing")
    size = run.get("fieldSize")
    if not isinstance(raw, list) or not raw or type(size) is not int or size < 3:
        return None
    if any(type(n) not in (int, float) or not isfinite(n) or not 1 <= n <= size for n in raw):
        return None
    return raw


def _distance(value):
    result = _finite(value)
    return result if result is not None and result > 0 else None


def public_pace_factors(race):
    """Mineta-style public observations as features, not a subjective ◎.

    Previous top-three corner position, distance change, neighbouring forward
    runners, and objectively sourced first-corner distance are independent
    observable inputs. Missing inputs stay unknown, never backward/slow.
    """
    if not isinstance(race, dict) or not isinstance(race.get("horses"), list):
        raise ValueError("full race detail required")
    if (race.get("track") in ("帯広", "帯広ば")
            or race.get("surface") in ("ばんえい", "障害")
            or race.get("analysisMode") in ("ばんえい", "障害")):
        raise ValueError("retired Banei and jumps cannot become flat-race predictions")
    circuit = race.get("circuit")
    if circuit not in ("中央", "地方", "jra", "nar"):
        raise ValueError("registered circuit required")
    active = sorted((h for h in race["horses"] if isinstance(h, dict) and
                     not any(h.get(k) for k in ("scratched", "withdrawn", "cancelled"))
                     and str(h.get("status") or "") not in ("取消", "出走取消", "除外")),
                    key=lambda h: h.get("horseNumber", 0))
    nos = [h.get("horseNumber") for h in active]
    if len(nos) < 3 or any(type(no) is not int or no < 1 for no in nos) or len(nos) != len(set(nos)):
        raise ValueError("unambiguous active runners required")
    race_distance = _distance(race.get("distance"))
    corner = _verified_first_corner(race)
    entries = []
    for horse in active:
        runs = observed_runs(horse, race, limit=5)
        positions = [_positions(run) for run in runs]
        valid = [p for p in positions if p is not None]
        previous = runs[0] if runs else {}
        last_positions = _positions(previous)
        prior_distance = _distance(previous.get("distance"))
        change = ("unknown" if race_distance is None or prior_distance is None else
                  "extension" if race_distance > prior_distance else
                  "shortening" if race_distance < prior_distance else "same")
        last_early = any(p <= 3 for p in last_positions) if last_positions else None
        # Distance extension is only a forward-intent research *candidate*,
        # never evidence that a horse will actually lead the field.
        candidate = last_early is True or change == "extension"
        # The four display phases are explicitly historical observations, NOT
        # a fabricated prediction of today's positions. Corner labels are used
        # only when the source has an unambiguous four-corner sequence.
        phase_evidence = {
            "start": {"status": "unavailable", "observedPosition": None},
            "thirdCorner": {
                "status": "historical-observation" if last_positions and len(last_positions) == 4 else "unavailable",
                "observedPosition": last_positions[2] if last_positions and len(last_positions) == 4 else None,
            },
            "fourthCorner": {
                "status": "historical-observation" if last_positions and len(last_positions) == 4 else "unavailable",
                "observedPosition": last_positions[3] if last_positions and len(last_positions) == 4 else None,
            },
            "straight": {
                "status": "historical-finish" if type(previous.get("finish")) is int and previous["finish"] > 0 else "unavailable",
                "observedFinish": previous.get("finish") if type(previous.get("finish")) is int and previous["finish"] > 0 else None,
            },
        }
        # A cautious baseline from prior races only. This is a descriptive
        # projected relative rank, NOT an empirically calibrated race simulation.
        phase_projection = {"start": {"status": "unavailable", "projectedRank": None}}
        for key, index in (("thirdCorner", 2), ("fourthCorner", 3)):
            samples = [
                (row[index] - 1) / (run["fieldSize"] - 1)
                for run in runs for row in [_positions(run)]
                if row is not None and len(row) == 4 and run["fieldSize"] > 1
            ]
            phase_projection[key] = {
                "status": "historical-baseline-unvalidated" if samples else "unavailable",
                "observedStarts": len(samples),
                "meanRelativePosition": round(sum(samples) / len(samples), 6) if samples else None,
                "projectedRank": (
                    round(1 + (len(active) - 1) * sum(samples) / len(samples), 2)
                    if samples else None
                ),
            }
        finish_samples = [
            (run["finish"] - 1) / (run["fieldSize"] - 1)
            for run in runs if run["fieldSize"] > 1
        ]
        phase_projection["straight"] = {
            "status": "historical-baseline-unvalidated" if finish_samples else "unavailable",
            "observedStarts": len(finish_samples),
            "meanRelativePosition": round(sum(finish_samples) / len(finish_samples), 6) if finish_samples else None,
            "projectedRank": (
                round(1 + (len(active) - 1) * sum(finish_samples) / len(finish_samples), 2)
                if finish_samples else None
            ),
        }
        entries.append({
            "phaseProjection": phase_projection,
            "phaseEvidence": phase_evidence,
            "horseNumber": horse["horseNumber"],
            "lastRunDate": previous.get("_raceDate") or previous.get("date"),
            "lastFirstCornerTop3": last_early,
            "observedCornerStarts": len(valid),
            "pastEarlyTop3Share": (
                sum(any(p <= 3 for p in row) for row in valid) / len(valid)
                if valid else None),
            "lastRunDistanceChange": change,
            "forwardIntentCandidate": candidate if last_early is not None or
                                      change != "unknown" else None,
            "startingHorseNumber": horse["horseNumber"]
        })
    candidates = [e["horseNumber"] for e in entries if e["forwardIntentCandidate"] is True]
    candidate_set = set(candidates)
    adjacent = [[a, a + 1] for a in candidates if a + 1 in candidate_set]
    return {
        "version": VERSION,
        "circuit": circuit,
        "raceId": race.get("id"), "raceDate": race.get("date"),
        "firstCornerMetersOfficial": corner,
        "firstCornerShortPublicRule": corner < 300 if corner is not None else None,
        "forwardIntentCandidates": candidates,
        "adjacentForwardCandidates": adjacent,
        "forwardCandidateShare": len(candidates) / len(active),
        "horses": entries,
        "phaseOrder": ["start", "thirdCorner", "fourthCorner", "straight"],
        "phaseEvidenceKind": "past-race-observations-only",
        "phaseProjectionKind": "historical-relative-rank-baseline-not-calibrated",
        "predictedActualLead": False,
        "predictedPaceProbabilities": None,
        "winProbability": None,
        "status": "measured-public-method-inputs-only",
    }
