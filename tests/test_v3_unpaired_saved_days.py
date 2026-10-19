"""Stage 32: unpaired days must not disappear from saved-week evidence."""
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1] / "arvexq" / "ui" / "static"

from arvexq.v3.audit.full_archive import verify_saved_week


def test_unpaired_manifest_day_within_window_is_an_integrity_failure(tmp_path):
    cards = tmp_path / "racecards"
    snapshots = tmp_path / "saved-snapshots"
    cards.mkdir()
    snapshots.mkdir()
    for day in ("2026-10-12", "2026-10-14"):
        (cards / f"{day}.json").write_bytes((ROOT / "racecards" / f"{day}.json").read_bytes())
        (snapshots / f"{day}.json").write_bytes((ROOT / "saved-snapshots" / f"{day}.json").read_bytes())
    (snapshots / "2026-10-13.json").write_text('{"races":{}}', encoding="utf-8")
    report = verify_saved_week(tmp_path, days=2)
    assert report["dateRange"] == ["2026-10-12", "2026-10-14"]
    assert report["unpairedSavedDays"] == [
        {"date": "2026-10-13", "filePresence": "manifest-only"}
    ]
    assert {"date": "2026-10-13", "code": "unpaired-saved-day",
            "filePresence": "manifest-only"} in report["errors"]
    assert report["allIndexedSavedOriginalsVerified"] is False


def test_unpaired_racecard_day_is_reported_without_claiming_official_gap(tmp_path):
    cards = tmp_path / "racecards"
    snapshots = tmp_path / "saved-snapshots"
    cards.mkdir()
    snapshots.mkdir()
    for day in ("2026-10-12", "2026-10-14"):
        (cards / f"{day}.json").write_bytes((ROOT / "racecards" / f"{day}.json").read_bytes())
        (snapshots / f"{day}.json").write_bytes((ROOT / "saved-snapshots" / f"{day}.json").read_bytes())
    (cards / "2026-10-13.json").write_text('{"races":[]}', encoding="utf-8")
    report = verify_saved_week(tmp_path, days=2)
    assert report["unpairedSavedDays"] == [
        {"date": "2026-10-13", "filePresence": "racecard-only"}
    ]
    assert report["officialPublishedRacesVerified"] is False
    assert report["allIndexedSavedOriginalsVerified"] is False


def test_trailing_unpaired_manifest_cannot_disappear_after_last_pair(tmp_path):
    cards = tmp_path / "racecards"
    snapshots = tmp_path / "saved-snapshots"
    cards.mkdir()
    snapshots.mkdir()
    for day in ("2026-10-12", "2026-10-14"):
        (cards / f"{day}.json").write_bytes((ROOT / "racecards" / f"{day}.json").read_bytes())
        (snapshots / f"{day}.json").write_bytes((ROOT / "saved-snapshots" / f"{day}.json").read_bytes())
    (snapshots / "2026-10-15.json").write_text('{"races":{}}', encoding="utf-8")
    report = verify_saved_week(tmp_path, days=2)
    assert report["unpairedSavedDays"] == [
        {"date": "2026-10-15", "filePresence": "manifest-only"}
    ]
    assert report["allIndexedSavedOriginalsVerified"] is False
    assert report["dateRange"] == ["2026-10-12", "2026-10-14"]
    assert report["integrityScanRange"] == ["2026-10-12", "2026-10-15"]
    assert report["integrityScanCalendarDays"] == 4


def test_trailing_unpaired_racecard_cannot_disappear_after_last_pair(tmp_path):
    cards = tmp_path / "racecards"
    snapshots = tmp_path / "saved-snapshots"
    cards.mkdir()
    snapshots.mkdir()
    for day in ("2026-10-12", "2026-10-14"):
        (cards / f"{day}.json").write_bytes((ROOT / "racecards" / f"{day}.json").read_bytes())
        (snapshots / f"{day}.json").write_bytes((ROOT / "saved-snapshots" / f"{day}.json").read_bytes())
    (cards / "2026-10-15.json").write_text('{"races":[]}', encoding="utf-8")
    report = verify_saved_week(tmp_path, days=2)
    assert report["unpairedSavedDays"] == [
        {"date": "2026-10-15", "filePresence": "racecard-only"}
    ]
    assert report["officialPublishedRacesVerified"] is False
    assert report["allIndexedSavedOriginalsVerified"] is False
    assert report["integrityScanRange"] == ["2026-10-12", "2026-10-15"]


def test_explicit_end_date_excludes_later_unpaired_files(tmp_path):
    cards = tmp_path / "racecards"
    snapshots = tmp_path / "saved-snapshots"
    cards.mkdir()
    snapshots.mkdir()
    for day in ("2026-10-12", "2026-10-14"):
        (cards / f"{day}.json").write_bytes((ROOT / "racecards" / f"{day}.json").read_bytes())
        (snapshots / f"{day}.json").write_bytes((ROOT / "saved-snapshots" / f"{day}.json").read_bytes())
    (snapshots / "2026-10-15.json").write_text('{"races":{}}', encoding="utf-8")
    report = verify_saved_week(tmp_path, days=2, end_date="2026-10-14")
    assert report["unpairedSavedDays"] == []
    assert report["integrityScanRange"] == ["2026-10-12", "2026-10-14"]
    assert not any(error["code"] == "unpaired-saved-day" for error in report["errors"])
    # Fixture omits gzip originals; do not claim full archive integrity.
    assert report["allIndexedSavedOriginalsVerified"] is False


@pytest.mark.parametrize("bad_end_date", ["20261014", "2026-10-4", "2026-13-01"])
def test_end_date_requires_canonical_calendar_date(tmp_path, bad_end_date):
    with pytest.raises(ValueError):
        verify_saved_week(tmp_path, days=1, end_date=bad_end_date)
