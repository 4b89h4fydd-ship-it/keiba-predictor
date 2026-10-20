"""Read-only archived factual evidence gate for the existing NAR/JRA data path.

Archived originals only: SHA-verified, cannot prove current D1/API/UI parity,
official payout completeness, first start, or current live acquisition coverage.
No HTTP calls, D1 writes, or replacement provider.
"""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path

from arvexq.v3.audit.snapshot_digest import verify_one

ARCHIVE = Path(__file__).resolve().parents[1] / "arvexq" / "ui" / "static"
RESEARCH = Path(__file__).resolve().parents[1] / "docs" / "research" / "stage64-results"


def _day(day: str) -> dict:
    card = json.loads((ARCHIVE / "racecards" / (day + ".json")).read_text(encoding="utf-8"))
    manifest = json.loads((ARCHIVE / "saved-snapshots" / (day + ".json")).read_text(encoding="utf-8"))
    assert card["date"] == day == manifest["date"]
    assert len(card["races"]) == card["raceCount"] == len(manifest["races"])
    return {"card": card, "manifest": manifest}


def _audit_day(day: str) -> dict:
    documents = _day(day)
    races = documents["card"]["races"]
    refs = documents["manifest"]["races"]
    counts = {"jra": Counter(), "nar": Counter()}
    reasons = {"jra": Counter(), "nar": Counter()}
    evidence = []
    for race in races:
        rid = race["id"]
        circuit = rid.split("-", 1)[0]
        assert circuit in counts
        assert ((circuit == "jra" and race["circuit"] in ("中央", "jra")) or
                (circuit == "nar" and race["circuit"] in ("地方", "nar")))
        result = verify_one(
            ARCHIVE / "saved-snapshots", rid, refs[rid],
            day=day, circuit=circuit, card_horses=race["horses"],
            verify_history=True,
        )
        history = result["historyAudit"]
        assert history["lifetimeCompleteness"] == "unverified"
        assert not history["sameOrFutureDirectRows"]
        assert not history["invalidDirectDateRows"]
        assert (len(history["noObservedPriorCases"]) +
                history["runnersWithObservedPriorRuns"] == result["runnerRows"])
        counts[circuit]["races"] += 1
        counts[circuit]["runners"] += result["runnerRows"]
        counts[circuit]["zeroPriorObserved"] += len(history["noObservedPriorCases"])
        counts[circuit]["observedPriorRunRows"] += history["observedPriorRunRows"]
        counts[circuit]["careerSidecarsVerified"] += history["careerSidecarsVerified"]
        for h in history["noObservedPriorCases"]:
            assert h["debutConfirmed"] is False
            assert h["completeHistoryVerified"] is False
            reasons[circuit][h["category"]] += 1
            evidence.append({
                "raceId": h["raceId"], "horseNumber": h["horseNumber"],
                "name": h["horseName"], "age": h["age"],
                "category": h["category"],
                "reportedStartsAsOfRace": h["reportedStartsAsOfRace"],
            })
    return {
        "savedDate": day,
        "source": "git-archived-hash-verified-snapshots-not-current-d1",
        "circuits": {k: dict(v) for k, v in counts.items()},
        "zeroPriorReasonCounts": {k: dict(v) for k, v in reasons.items()},
        "zeroPriorCases": evidence,
        "liveD1ReadbackVerified": False,
        "officialPublishedResultVerified": False,
        "completeLifetimeHistoryVerified": False,
    }


def test_20261016_nar_originals_missing_history_are_exposed_not_inferred():
    result = _audit_day("2026-10-16")
    assert result["circuits"]["nar"]["races"] == 36
    assert result["circuits"]["jra"] == {}
    assert result["circuits"]["nar"]["runners"] == 362
    assert result["circuits"]["nar"]["zeroPriorObserved"] == len(result["zeroPriorCases"])
    print("ARVEXQ_ARCHIVED_20261016_HISTORY_EVIDENCE=" +
          json.dumps({k: v for k, v in result.items() if k != "zeroPriorCases"},
                     ensure_ascii=False, sort_keys=True))
    # Existing saved race details can only reveal unknown prior history; they
    # cannot certify a first lifetime start or fix a missing past run.
    assert result["liveD1ReadbackVerified"] is False


def test_20261018_jra_original_history_does_not_confirm_first_starts():
    result = _audit_day("2026-10-18")
    assert result["circuits"]["jra"]["races"] > 0
    assert result["circuits"]["nar"]["races"] > 0
    assert result["circuits"]["jra"]["zeroPriorObserved"] >= 0
    assert result["completeLifetimeHistoryVerified"] is False
    print("ARVEXQ_ARCHIVED_20261018_HISTORY_EVIDENCE=" +
          json.dumps({k: v for k, v in result.items() if k != "zeroPriorCases"},
                     ensure_ascii=False, sort_keys=True))


def test_existing_official_archive_gap_recheck_does_not_claim_recovery():
    path = RESEARCH / "official_gap_recheck.json"
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["schema"] == "arvexq-stage64-official-gap-recheck-1"
    obs = saved["observations"]
    assert len(obs) == saved["targetHorses"] == 34
    assert len({o["raceId"] for o in obs}) == saved["targetRaces"] == 11
    assert sum(o["validPriorRuns"] > 0 for o in obs) == saved["withValidPriorEvidence"]
    assert all(o["fullCareerVerified"] is False for o in obs)
    assert all(o["status"] == "unresolved" for o in obs)
    print("ARVEXQ_OFFICIAL_ARCHIVE_RECHECK=" + json.dumps({
        "targetRaces": saved["targetRaces"],
        "targetHorses": saved["targetHorses"],
        "withValidPriorEvidence": saved["withValidPriorEvidence"],
        "reasons": dict(Counter(o["reason"] for o in obs)),
        "limitation": "bounded-supplied-official-archives-not-current-data",
    }, ensure_ascii=False, sort_keys=True))
