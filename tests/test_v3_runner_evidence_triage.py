"""Pure missing-history and carried-weight evidence classifications."""
from copy import deepcopy
from pathlib import Path

import pytest

from arvexq.v3.audit.runner_gaps import (
    classify_absent_prior, compare_saved_weight, summarize_evidence
)
from arvexq.v3.audit.full_archive import verify_saved_week


def sample_horse():
    return {"horseNumber": 3, "name": "検査馬", "age": 2, "allPastRuns": [], "recentRaces": []}


def sample_race(title="2歳未勝利"):
    return {"id": "jra-2026-10-18-京都-01", "date": "2026-10-18",
            "track": "京都", "title": title}


def test_absence_does_not_make_debut():
    h = sample_horse()
    before = deepcopy(h)
    gap = classify_absent_prior(h, sample_race())
    assert gap["category"] == "no-prior-runs-unverified"
    assert gap["debutConfirmed"] is False
    assert h == before


def test_debut_card_only_means_context():
    h = sample_horse()
    r = classify_absent_prior(h, sample_race("2歳新馬"))
    assert r["category"] == "debut-race-without-dated-start-evidence"
    assert r["debutConfirmed"] is False


def test_dated_reported_starts_are_explicit_evidence_not_guess():
    horse = sample_horse()
    horse["careerStartEvidence"] = {"asOfRaceDate": "2026-10-18", "starts": 3,
                                     "source": "verified-source-identifier"}
    r = classify_absent_prior(horse, sample_race())
    assert r["category"] == "reported-prior-starts-not-observed"
    assert r["reportedStartsAsOfRace"] == 3
    horse["careerStartEvidence"]["starts"] = 0
    r = classify_absent_prior(horse, sample_race())
    assert r["category"] == "dated-source-reports-zero-starts"
    assert r["debutConfirmed"] is False
    horse["careerStartEvidence"]["asOfRaceDate"] = "2026-10-20"
    assert classify_absent_prior(horse, sample_race())["category"] == "no-prior-runs-unverified"


def test_saved_source_weight_gap_reasons_do_not_fabricate():
    card = sample_horse()
    card.pop("carriedWeight", None)
    other = {**card, "carriedWeight": 580}
    present = compare_saved_weight(card, other, sample_race())
    assert present["sourceState"] == "saved-original-has-carriedWeight-card-blank"
    assert present["savedOriginalCarriedWeight"] == 580
    assert present["inferredValue"] is None
    alternate = compare_saved_weight(card, {**card, "weight": 570}, sample_race())
    assert alternate["sourceState"] == "saved-original-other-weight-key-card-blank"
    both = compare_saved_weight(card, card, sample_race())
    assert both["sourceState"] == "saved-original-and-card-both-blank"
    assert compare_saved_weight({**card, "carriedWeight": 570}, other, sample_race()) is None


def test_saved_week_accounts_for_all_295_unknown_prior_histories_without_fabrication():
    root = Path(__file__).resolve().parents[1] / "arvexq" / "ui" / "static"
    report = verify_saved_week(root, days=7, end_date="2026-10-18")
    triage = report["runnerEvidenceTriage"]
    assert triage["zeroObservedPriorRuns"] == 295
    assert triage["missingCardCarriedWeight"] == 29
    assert sum(sum(d.values()) for d in triage["byCircuitCategory"].values()) == 295
    assert sum(triage["missingWeightByState"].values()) == 29
    assert triage["confirmedDebutCount"] == 0
    assert triage["officialPastStartsCompared"] is False
    assert triage["predictionStatus"] == "not-implemented"
    assert all(not c["debutConfirmed"] for c in triage["noPriorRunCases"])
