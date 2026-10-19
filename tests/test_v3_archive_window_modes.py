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


def test_calendar_window_reports_missing_day_without_certifying_race_coverage():
    from arvexq.v3.audit.calendar_window import calendar_window
    window = calendar_window(["2026-10-12", "2026-10-14", "2026-10-15"])
    assert window["selectedSavedDays"] == 3
    assert window["calendarSpanDays"] == 4
    assert window["missingCalendarDays"] == ["2026-10-13"]
    assert window["consecutiveCalendarDays"] is False
    assert window["officialRaceDayCoverageVerified"] is False
    good = calendar_window(["2026-10-12", "2026-10-13"])
    assert good["consecutiveCalendarDays"] is True
    assert good["officialRaceDayCoverageVerified"] is False
    for bad in (["2026-10-14", "2026-10-12"],
                ["2026-10-12", "2026-10-12"], ["2026-02-30"]):
        with pytest.raises(ValueError):
            calendar_window(bad)


@pytest.mark.parametrize("reader", [
    lambda: audit_cards(days=2, end_date="2026-10-18"),
    lambda: audit_digests(days=2, per_circuit=1, end_date="2026-10-18"),
    lambda: verify_saved_week(ROOT, days=2, end_date="2026-10-18"),
])
def test_archive_report_exposes_calendar_evidence_not_official_completeness(reader):
    report = reader()
    window = report["calendarWindow"]
    assert window["selectedDates"] == ["2026-10-17", "2026-10-18"]
    assert window["selectedSavedDays"] == 2
    assert window["calendarSpanDays"] == 2
    assert window["missingCalendarDays"] == []
    assert window["consecutiveCalendarDays"] is True
    assert window["officialRaceDayCoverageVerified"] is False


def test_real_saved_archive_pairs_report_gap_without_inventing_missing_day(tmp_path):
    """Exercise the archive audit on actual unchanged Oct 17/19 paired files."""
    (tmp_path / "racecards").mkdir()
    (tmp_path / "saved-snapshots").mkdir()
    for day in ("2026-10-17", "2026-10-19"):
        for folder in ("racecards", "saved-snapshots"):
            name = day + ".json"
            source = ROOT / folder / name
            assert source.is_file()
            (tmp_path / folder / name).write_bytes(source.read_bytes())
    original = {
        (folder, day): (ROOT / folder / (day + ".json")).read_bytes()
        for folder in ("racecards", "saved-snapshots")
        for day in ("2026-10-17", "2026-10-19")
    }
    report = audit_cards(directory=tmp_path, days=2, samples_per_circuit=0)
    window = report["calendarWindow"]
    assert window["selectedDates"] == ["2026-10-17", "2026-10-19"]
    assert window["selectedSavedDays"] == 2
    assert window["calendarSpanDays"] == 3
    assert window["missingCalendarDays"] == ["2026-10-18"]
    assert window["consecutiveCalendarDays"] is False
    assert window["officialRaceDayCoverageVerified"] is False
    assert report["dateCount"] == 2
    assert report["structuralProblems"] == 0
    for (folder, day), content in original.items():
        assert (ROOT / folder / (day + ".json")).read_bytes() == content
    # The cutoff filters selected saved observations, not the missing day.
    report = audit_cards(directory=tmp_path, days=1, end_date="2026-10-18")
    assert report["calendarWindow"]["selectedDates"] == ["2026-10-17"]
    with pytest.raises(ValueError, match="insufficient"):
        audit_cards(directory=tmp_path, days=2, end_date="2026-10-18")


def test_unpaired_newest_day_does_not_erase_existing_gap_evidence(tmp_path):
    (tmp_path / "racecards").mkdir()
    (tmp_path / "saved-snapshots").mkdir()
    for day in ("2026-10-17", "2026-10-19"):
        for folder in ("racecards", "saved-snapshots"):
            name = day + ".json"
            (tmp_path / folder / name).write_bytes((ROOT / folder / name).read_bytes())
    (tmp_path / "racecards" / "2026-10-20.json").write_text("{}")
    report = audit_cards(directory=tmp_path, days=2)
    assert report["calendarWindow"]["missingCalendarDays"] == ["2026-10-18"]
    assert report["calendarWindow"]["selectedDates"][-1] == "2026-10-19"


def test_calendar_gaps_are_not_asserted_as_cancelled_or_unsaved_races():
    from arvexq.v3.audit.calendar_window import calendar_window
    report = calendar_window(["2026-02-27", "2026-03-02"])
    assert report["missingCalendarDays"] == ["2026-02-28", "2026-03-01"]
    assert [d["date"] for d in report["missingDayEvidence"]] == report["missingCalendarDays"]
    assert all(d["officialRaceSchedule"] == "unverified"
               and d["savedPair"] == "not-selected"
               and "unknown" in d["reason"]
               for d in report["missingDayEvidence"])
    assert report["officialRaceDayCoverageVerified"] is False
    leap = calendar_window(["2028-02-28", "2028-03-01"])
    assert leap["missingCalendarDays"] == ["2028-02-29"]
    assert leap["missingDayEvidence"][0]["officialRaceSchedule"] == "unverified"
    contiguous = calendar_window(["2026-10-18", "2026-10-19"])
    assert contiguous["missingDayEvidence"] == []


@pytest.mark.parametrize("kind", [
    "neither-present", "racecard-only", "manifest-only", "both-present"
])
def test_missing_selected_day_records_filesystem_evidence_without_claiming_racing(tmp_path, kind):
    from arvexq.v3.audit.calendar_window import calendar_window
    (tmp_path / "racecards").mkdir()
    (tmp_path / "saved-snapshots").mkdir()
    if kind in ("racecard-only", "both-present"):
        (tmp_path / "racecards" / "2026-10-18.json").write_text("{}")
    if kind in ("manifest-only", "both-present"):
        (tmp_path / "saved-snapshots" / "2026-10-18.json").write_text("{}")
    row = calendar_window(["2026-10-17", "2026-10-19"],
                          archive_dir=tmp_path)["missingDayEvidence"][0]
    assert row["filePresence"] == kind
    assert row["savedPair"] == "not-selected"
    assert row["officialRaceSchedule"] == "unverified"


def test_actual_audit_distinguishes_unpaired_gap_file_from_absent_date(tmp_path):
    for folder in ("racecards", "saved-snapshots"):
        (tmp_path / folder).mkdir()
    for day in ("2026-10-17", "2026-10-19"):
        for folder in ("racecards", "saved-snapshots"):
            name = day + ".json"
            (tmp_path / folder / name).write_bytes((ROOT / folder / name).read_bytes())
    missing = audit_cards(directory=tmp_path, days=2)
    assert missing["calendarWindow"]["missingDayEvidence"][0]["filePresence"] == "neither-present"
    (tmp_path / "racecards" / "2026-10-18.json").write_text("{}")
    incomplete = audit_cards(directory=tmp_path, days=2)
    assert incomplete["calendarWindow"]["missingDayEvidence"][0]["filePresence"] == "racecard-only"
    assert incomplete["calendarWindow"]["selectedDates"] == ["2026-10-17", "2026-10-19"]
    assert incomplete["calendarWindow"]["officialRaceDayCoverageVerified"] is False
