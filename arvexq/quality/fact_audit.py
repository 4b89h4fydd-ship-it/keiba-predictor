"""Measure observed field gaps and historical evidence without prediction scores."""
from __future__ import annotations
from collections import Counter
import math

from arvexq.ingest.runner_identity_compare import compare_same_day_runner
from arvexq.ingest.circuit_transfer import race_circuit
from arvexq.ingest.race_identity import observed_detail_identity_error
from arvexq.ingest.source_provenance import observed_provenance
from arvexq.ingest.career_transport import recover_horse
from arvexq.ingest.full_career import date_key, merge_career

RACE_FIELDS = ("distance", "surface", "weather", "condition", "startTime")
HORSE_FIELDS = ("horseNumber", "frameNumber", "name", "sex", "age", "carriedWeight",
                "jockey", "trainer", "affiliation", "bodyWeight", "bodyWeightChange")
POSITIVE = {"distance", "horseNumber", "frameNumber", "age", "carriedWeight", "bodyWeight"}


def observed(field, value):
    if value in (None, "", "不明", "--", "-", [], {}):
        return False
    if field in POSITIVE or field == "bodyWeightChange":
        try:
            number = float(value)
            return (not isinstance(value, bool) and math.isfinite(number)
                    and (field == "bodyWeightChange" or number > 0))
        except (TypeError, ValueError):
            return False
    return True


def audit_day(bundle):
    counts, race_gaps, horse_gaps = Counter(), Counter(), Counter()
    errors = []
    first_race_by_circuit = {}
    for detail in bundle.get("details") or []:
        mismatch = observed_detail_identity_error(detail)
        if mismatch:
            errors.append(mismatch)
        counts["races"] += 1
        for field in RACE_FIELDS:
            race_gaps[field] += not observed(field, detail.get(field))
        # Names are only collision evidence within the same observed circuit.
        # Unknown circuits stay separate; never assume they are JRA or NAR.
        first_race_by_name = first_race_by_circuit.setdefault(race_circuit(detail), {})
        seen = set()
        for horse in detail.get("horses") or []:
            if not isinstance(horse, dict):
                errors.append({"raceId": detail["id"], "error": "runner is not an object"})
                continue
            counts["horses"] += 1
            for field in HORSE_FIELDS:
                horse_gaps[field] += not observed(field, horse.get(field))
            collision = compare_same_day_runner(
                first_race_by_name, race_id=detail["id"],
                horse_name=horse.get("name"), horse_number=horse.get("horseNumber"))
            if collision:
                collision.update(observed_provenance(detail, horse))
                errors.append(collision)
            number = horse.get("horseNumber")
            if observed("horseNumber", number):
                numeric = float(number)
                identity = int(numeric) if numeric.is_integer() else str(number)
                if not numeric.is_integer() or not 1 <= numeric <= 18:
                    errors.append({"raceId": detail["id"], "horseNumber": number,
                                   "error": "horse number outside 1..18"})
                if identity in seen:
                    errors.append({"raceId": detail["id"], "horseNumber": number,
                                   "error": "duplicate runner identity"})
                seen.add(identity)
            frame = horse.get("frameNumber")
            if observed("frameNumber", frame):
                numeric = float(frame)
                if not numeric.is_integer() or not 1 <= numeric <= 8:
                    error = {"raceId": detail["id"], "horseNumber": number,
                             "frameNumber": frame, "horseName": horse.get("name"),
                             "error": "frame number outside 1..8"}
                    error.update(observed_provenance(detail, horse))
                    errors.append(error)
            try:
                restored = recover_horse(horse, detail["date"])
                raw = (horse.get("allPastRuns") or []) + (horse.get("recentRaces") or [])
                future = {date_key(row.get("date") or row.get("raceDate")) for row in raw
                          if isinstance(row, dict)}
                future = {day for day in future if day and day >= detail["date"]}
                counts["futureHistoryDates"] += len(future)
                if future:
                    errors.append({"raceId": detail["id"], "horseNumber": number,
                                   "error": "non-prior history dates", "dates": sorted(future)})
                runs = merge_career(restored.get("allPastRuns"), restored.get("recentRaces"), detail["date"])
                counts["observedPriorRuns"] += len(runs)
                counts["horsesWithoutObservedPriorRuns"] += not runs
                counts["verifiedCareerArchives"] += isinstance(horse.get("careerArchive"), dict)
            except (ValueError, KeyError, TypeError, OSError) as exc:
                errors.append({"raceId": detail["id"], "horseNumber": number,
                               "error": "career recovery: " + str(exc)[:160]})
    read_errors = list(bundle.get("readErrors") or [])
    expected = len(bundle.get("races") or [])
    return {"date": bundle["date"], "summaryRaces": expected,
            "observed": dict(counts), "missingRaceFields": dict(race_gaps),
            "missingHorseFields": dict(horse_gaps), "readErrors": read_errors,
            "validationErrors": errors,
            "displayFallbackRaces": sum(v == "display" for v in (bundle.get("readbackSources") or {}).values()),
            "allRaceReadsVerified": bool(expected) and counts["races"] == expected and not read_errors,
            "predictionLogicStatus": "予想ロジック仕様待ち"}
