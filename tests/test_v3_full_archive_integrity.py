"""Exhaustive saved race file checksum and career archive regression."""
import json
from pathlib import Path
import pytest

from arvexq.v3.audit.full_archive import verify_saved_week
from arvexq.v3.audit.snapshot_digest import verify_one


ROOT=Path(__file__).resolve().parents[1]/"arvexq"/"ui"/"static"


def test_full_saved_week_integrity_preserves_unknown_official_completeness():
    report=verify_saved_week(ROOT,days=7)
    assert report["expectedRacecards"]==423
    assert report["circuits"]["jra"]["expected"]==96
    assert report["circuits"]["nar"]["expected"]==327
    assert report["predictionStatus"]=="not-implemented"
    assert report["officialPublishedRacesVerified"] is False
    assert report["completeLifetimeHistoryVerified"] is False
    assert report["liveD1ReadbackVerified"] is False
    # Fail when any preserved original or its career sidecar is defective.
    assert report["allIndexedSavedOriginalsVerified"],report["errors"][:12]


def test_direct_prior_run_counts_are_not_lifetime_completeness():
    day="2026-10-18"
    card=json.loads((ROOT/"racecards"/(day+".json")).read_text())
    manifest=json.loads((ROOT/"saved-snapshots"/(day+".json")).read_text())
    row=next(r for r in card["races"] if r["id"]=="nar-2026-10-18-高知-01")
    report=verify_one(ROOT/"saved-snapshots",row["id"],manifest["races"][row["id"]],
                       day=day,circuit="nar",card_horses=row["horses"],verify_history=True)
    assert report["status"]=="verified"
    assert report["historyAudit"]["lifetimeCompleteness"]=="unverified"
