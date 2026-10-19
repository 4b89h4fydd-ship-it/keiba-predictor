"""Fixed historical reference windows must not replace rolling saved-pair audits."""
from pathlib import Path
import pytest

from scripts.arvexq_v3_archive_audit import audit_days as audit_cards
from scripts.arvexq_v3_blob_digest_audit import audit_days as audit_digests
from arvexq.v3.audit.full_archive import verify_saved_week

ROOT = Path(__file__).resolve().parents[1] / "arvexq" / "ui" / "static"


def paired_days():
    return sorted(
        p.stem for p in (ROOT / "racecards").glob("????-??-??.json")
        if (ROOT / "saved-snapshots" / p.name).is_file()
    )


@pytest.mark.parametrize("reader", [
    lambda: audit_cards(days=1),
    lambda: audit_digests(days=1, per_circuit=1),
    lambda: verify_saved_week(ROOT, days=1),
])
def test_default_audit_tracks_newest_paired_archive(reader):
    last = paired_days()[-1]
    report = reader()
    dates = report.get("dateRange", [report.get("start"), report.get("end")])
    assert dates == [last, last]


@pytest.mark.parametrize("reader", [
    lambda: audit_cards(days=1, end_date="2026-10-18"),
    lambda: audit_digests(days=1, per_circuit=1, end_date="2026-10-18"),
    lambda: verify_saved_week(ROOT, days=1, end_date="2026-10-18"),
])
def test_reference_cutoff_is_fixed_not_rolling(reader):
    report = reader()
    dates = report.get("dateRange", [report.get("start"), report.get("end")])
    assert dates == ["2026-10-18", "2026-10-18"]


@pytest.mark.parametrize("reader", [
    lambda: audit_cards(days=1, end_date="2000-01-01"),
    lambda: audit_digests(days=1, per_circuit=1, end_date="2000-01-01"),
    lambda: verify_saved_week(ROOT, days=1, end_date="2000-01-01"),
])
def test_cutoff_without_paired_archives_fails_closed(reader):
    with pytest.raises(ValueError, match="insufficient|not enough"):
        reader()
