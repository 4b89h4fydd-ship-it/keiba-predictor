"""Evidence-only classification of missing saved past runs and carried weights.

Does not fetch, infer debut, fabricate carried weight, or use race results.
A reported 'zero prior starts' is only as reliable as date-bound evidence.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

from arvexq.ingest.full_career import audit_career, date_key


def _blank(value: Any) -> bool:
    return value is None or isinstance(value, str) and value.strip() in ("", "-", "--", "不明")


def classify_absent_prior(horse: dict[str, Any], race: dict[str, Any]) -> dict[str, Any]:
    race_date = date_key(race.get("date"))
    evidence = audit_career(horse, race_date, requested=0, providers=[])
    if evidence["observedRuns"]:
        raise ValueError("horse has recorded prior runs; cannot classify as absent")
    reported = evidence.get("reportedStarts")
    title = str(race.get("title") or "")
    if reported is not None and reported > 0:
        category = "reported-prior-starts-not-observed"
    elif reported == 0:
        category = "dated-source-reports-zero-starts"
    elif "新馬" in title:
        category = "debut-race-without-dated-start-evidence"
    else:
        category = "no-prior-runs-unverified"
    # Source declaration can contain older or conflicting information;
    # never convert race title, age or empty list into a first-start fact.
    return {
        "raceId": str(race.get("id") or ""),
        "raceDate": race_date,
        "track": str(race.get("track") or ""),
        "raceTitle": title,
        "horseNumber": horse.get("horseNumber"),
        "horseName": str(horse.get("name") or ""),
        "age": horse.get("age"),
        "category": category,
        "reportedStartsAsOfRace": reported,
        "reportedStartsSource": evidence.get("reportedStartsSource"),
        "coverageStatus": evidence["status"],
        "careerSidecarPresent": isinstance(horse.get("careerArchive"), dict),
        "careerHistoryAuditCompleteFlag": (
            (horse.get("_careerHistoryAudit") or {}).get("complete") is True
            if isinstance(horse.get("_careerHistoryAudit"), dict) else False),
        "debutConfirmed": False,
        "completeHistoryVerified": False,
    }


def compare_saved_weight(card_horse: dict[str, Any],
                         saved_horse: dict[str, Any], race: dict[str, Any]) -> dict | None:
    """Only report a missing published weight; never invent a carried weight."""
    observed = card_horse.get("carriedWeight")
    if not _blank(observed):
        return None
    original = saved_horse.get("carriedWeight")
    alt = saved_horse.get("weight")
    if not _blank(original):
        state = "saved-original-has-carriedWeight-card-blank"
    elif not _blank(alt):
        state = "saved-original-other-weight-key-card-blank"
    else:
        state = "saved-original-and-card-both-blank"
    return {
        "raceId": str(race.get("id") or ""),
        "date": race.get("date"),
        "track": str(race.get("track") or ""),
        "horseNumber": card_horse.get("horseNumber"),
        "horseName": str(card_horse.get("name") or ""),
        "field": "carriedWeight",
        "sourceState": state,
        "savedOriginalCarriedWeight": original if state == "saved-original-has-carriedWeight-card-blank" else None,
        "alternateKeyPresent": not _blank(alt),
        "inferredValue": None,
    }


def summarize_evidence(no_prior: list[dict], missing_weight: list[dict]) -> dict:
    by_circuit: dict[str, Counter] = {c: Counter() for c in ("jra", "nar")}
    by_track: dict[str, Counter] = {}
    for case in no_prior:
        circuit = ("jra" if str(case["raceId"]).startswith("jra-") else
                   "nar" if str(case["raceId"]).startswith("nar-") else "unknown")
        by_circuit.setdefault(circuit, Counter())[case["category"]] += 1
        by_track.setdefault(circuit + ":" + str(case["track"]), Counter())[case["category"]] += 1
    return {
        "schema": "arvexq-v3-runner-evidence-triage-1",
        "zeroObservedPriorRuns": len(no_prior),
        "byCircuitCategory": {key: dict(sorted(c.items())) for key, c in by_circuit.items()},
        "byTrackCategory": {key: dict(sorted(c.items())) for key, c in sorted(by_track.items())},
        "missingCardCarriedWeight": len(missing_weight),
        "missingWeightByState": dict(sorted(Counter(
            item["sourceState"] for item in missing_weight).items())),
        "noPriorRunCases": no_prior,
        "carriedWeightCases": missing_weight,
        "officialPastStartsCompared": False,
        "confirmedDebutCount": 0,
        "predictionStatus": "not-implemented",
    }
