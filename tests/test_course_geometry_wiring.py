"""Course-geometry wiring tests (2026-11-25).

The verified first-corner value (the pace evidence module's
verifier, arvexq.prediction.mineta_public_pace's
``_verified_first_corner`` — the same check public_pace_factors
applies; main exposes no public wrapper under the name
``verified_first_corner_meters``, so both the lane and these
tests call the module's own verifier) reads ``courseGeometry``
off the race detail, but no lane ever attached one, so every
published pack carried firstCornerMetersOfficial null. The
publish lane now attaches the standing official record for the
race's (track, surface, distance) from
rewrite/data/course_geometry.json at the one consumer
(build_publish_detail, just before the value is read), and the
verifier re-checks the record against the race before anything
is published. api_shape's race_payload takes no first-corner
argument (its pace block hardcodes null), so the lane writes
the verified value into the built pace block — the composition
pinned below mirrors exactly that.

These tests pin:
  - the loader indexing all standing records, and degrading to
    {} when the file is missing/unreadable (publish proceeds
    exactly as before);
  - the attach: record found -> attached verbatim; no record
    (unpublished course) -> detail untouched; an attachment
    already present is never overridden;
  - the composition the lane performs (attach -> verify ->
    race_payload) landing the official value in
    detail.unifiedForecast.pace.firstCornerMetersOfficial for
    covered courses and staying None for uncovered ones;
  - the chronology guard end-to-end: a record whose publishedAt
    is after the race's off never lights up, even attached.
"""
from __future__ import annotations

from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from arvexq.prediction.mineta_public_pace import (
    _verified_first_corner as verified_first_corner_meters)
from rewrite.analysis.forecast import forecast_race
from rewrite.analysis.pace import forecast_pace
from rewrite.analysis.tickets import generate_tickets
from rewrite.data.normalize import normalize_race
from rewrite.output.api_shape import race_payload
from rewrite.test_analysis import CLOSER_RUNS, FRONT_RUNS, MID_RUNS, horse
from scripts.arvexq_rewrite_publish import (
    COURSE_GEOMETRY_PATH, _attach_course_geometry,
    _load_course_geometry)

PROVENANCE = {"snapshot_sha256": "a" * 64,
              "captured_at": "2026-11-25T01:00:00+09:00", "odds": []}


def _old(track, surface, distance, date="2026-12-01",
         start="15:00", **extra):
    detail = {"date": date, "track": track, "surface": surface,
              "distance": distance, "scheduledStartTime": start}
    detail.update(extra)
    return detail


def _payload_for(summary, horses, first_corner):
    race = normalize_race(summary, {"horses": horses}, "test://x")
    forecast = forecast_race(race, beta=2.0)
    pace = forecast_pace(race)
    odds = {r.number: r.win_odds.value
            for r in race.runners if r.win_odds.present}
    tickets = generate_tickets(forecast, odds,
                               calibration_validated=False)
    payload = race_payload(race, forecast, pace, tickets,
                           provenance=PROVENANCE)
    # The lane's adjusted composition: race_payload has no
    # first-corner parameter on main, so the verified value is
    # written into the built pace block after the payload is
    # built (build_publish_detail does exactly this).
    if first_corner is not None:
        payload["detail"]["unifiedForecast"]["pace"][
            "firstCornerMetersOfficial"] = first_corner
    return payload


URAWA_SUMMARY = {
    "race_id": "nar-2026-11-26-浦和-11", "race_date": "2026-11-26",
    "circuit": "地方", "track": "浦和", "race_no": 11,
    "start_time": "17:45", "title": "テスト", "surface": "ダート",
    "distance": 2000, "weather": "晴", "condition": "良",
    "updated_at": 1,
}

NAGOYA_SUMMARY = {
    "race_id": "nar-2026-11-26-名古屋-12", "race_date": "2026-11-26",
    "circuit": "地方", "track": "名古屋", "race_no": 12,
    "start_time": "17:30", "title": "テスト", "surface": "ダート",
    "distance": 1500, "weather": "晴", "condition": "良",
    "updated_at": 1,
}

HORSES = [horse(1, FRONT_RUNS), horse(2, CLOSER_RUNS),
          horse(3, MID_RUNS)]


class LoaderTests(TestCase):
    def test_repo_file_loads_all_records(self):
        index = _load_course_geometry()
        self.assertEqual(len(index), 154)
        self.assertEqual(
            index[("浦和", "ダート", 2000)]["firstCornerDistanceMeters"],
            300)
        self.assertEqual(
            index[("大井", "ダート", 1800)]["firstCornerDistanceMeters"],
            300)
        self.assertEqual(
            index[("京都", "ダート", 1800)]["firstCornerDistanceMeters"],
            285.8)

    def test_missing_file_degrades_to_empty(self):
        with patch("scripts.arvexq_rewrite_publish.COURSE_GEOMETRY_PATH",
                   Path("/nonexistent/course_geometry.json")):
            self.assertEqual(_load_course_geometry(), {})
            old = _old("浦和", "ダート", 2000)
            self.assertFalse(_attach_course_geometry(old))
            self.assertNotIn("courseGeometry", old)


class AttachTests(TestCase):
    def test_attach_covered_course(self):
        old = _old("浦和", "ダート", 2000, date="2026-11-25",
                   start="17:45")
        self.assertTrue(_attach_course_geometry(old))
        self.assertEqual(old["courseGeometry"]["sourceKind"],
                         "official_course_geometry")
        self.assertEqual(verified_first_corner_meters(old), 300.0)

    def test_attach_all_standing_records_verify(self):
        for (track, surface, distance), record in \
                _load_course_geometry().items():
            old = _old(track, surface, distance)
            self.assertTrue(_attach_course_geometry(old),
                            (track, surface, distance))
            self.assertEqual(
                verified_first_corner_meters(old),
                float(record["firstCornerDistanceMeters"]),
                (track, surface, distance))

    def test_uncovered_courses_stay_unattached(self):
        for args in [("大井", "ダート", 1400), ("名古屋", "ダート", 2000),
                     ("名古屋", "ダート", 920), ("中山", "芝", 2500),
                     ("新潟", "芝", 1000)]:
            old = _old(*args)
            self.assertFalse(_attach_course_geometry(old), args)
            self.assertNotIn("courseGeometry", old)
            self.assertIsNone(verified_first_corner_meters(old))

    def test_existing_attachment_never_overridden(self):
        sentinel = {"sourceKind": "official_course_geometry",
                    "marker": "acquisition-stage"}
        old = _old("浦和", "ダート", 2000, courseGeometry=sentinel)
        self.assertTrue(_attach_course_geometry(old))
        self.assertIs(old["courseGeometry"], sentinel)

    def test_chronology_guard_still_applies(self):
        # The Urawa record's publishedAt is 2026-11-11; a race
        # run before that must not light up even with the record
        # attached by this wiring.
        old = _old("浦和", "ダート", 2000, date="2026-11-01",
                   start="17:45")
        self.assertTrue(_attach_course_geometry(old))
        self.assertIsNone(verified_first_corner_meters(old))


class PackCompositionTests(TestCase):
    """The exact composition build_publish_detail performs:
    attach to the input detail, verify, build the payload with
    race_payload, write the verified value into the built pace
    block, read it back from the pack's pace block."""

    def test_covered_course_lands_official_value(self):
        old = _old("浦和", "ダート", 2000, date="2026-11-26",
                   start="17:45")
        _attach_course_geometry(old)
        payload = _payload_for(
            URAWA_SUMMARY, HORSES, verified_first_corner_meters(old))
        pace = payload["detail"]["unifiedForecast"]["pace"]
        self.assertEqual(pace["firstCornerMetersOfficial"], 300.0)

    def test_uncovered_course_stays_null(self):
        old = _old("名古屋", "ダート", 1500, date="2026-11-26",
                   start="17:30")
        _attach_course_geometry(old)
        payload = _payload_for(
            NAGOYA_SUMMARY, HORSES, verified_first_corner_meters(old))
        pace = payload["detail"]["unifiedForecast"]["pace"]
        self.assertIsNone(pace["firstCornerMetersOfficial"])
