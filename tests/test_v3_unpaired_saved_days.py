"""Stage 32: unpaired days must not disappear from saved-week evidence."""
from pathlib import Path

from arvexq.v3.audit.full_archive import verify_saved_week


def test_unpaired_manifest_day_within_window_is_an_integrity_failure(tmp_path):
    cards = tmp_path / "racecards"
    snapshots = tmp_path / "saved-snapshots"
    cards.mkdir()
    snapshots.mkdir()
    for day in ("2026-10-12", "2026-10-14"):
        (cards / f"{day}.json").write_text('{"races":[]}', encoding="utf-8")
        (snapshots / f"{day}.json").write_text('{"races":{}}', encoding="utf-8")
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
        (cards / f"{day}.json").write_text('{"races":[]}', encoding="utf-8")
        (snapshots / f"{day}.json").write_text('{"races":{}}', encoding="utf-8")
    (cards / "2026-10-13.json").write_text('{"races":[]}', encoding="utf-8")
    report = verify_saved_week(tmp_path, days=2)
    assert report["unpairedSavedDays"] == [
        {"date": "2026-10-13", "filePresence": "racecard-only"}
    ]
    assert report["officialPublishedRacesVerified"] is False
    assert report["allIndexedSavedOriginalsVerified"] is False
