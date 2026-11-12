"""Supply visibility for the rewrite publish lane (2026-11-12).

The 2026-11-12 incident: the v8 extras export had stopped the
night before, so when the 06:00 deferral deadline passed, all 48
of the day's races published on the v1 fallback — and the publish
run's own summary said nothing about the missing material, so
nobody noticed until the evening. Publishing must never block on
the shortage, but the run must now grade its own supply from the
lanes it leaves races standing on: counts carry v1Fallback /
extrasPresent / supplyAlert, a partial fallback prints a SUPPLY
WARNING naming the races, and a total fallback prints a SUPPLY
ALERT plus the alert record (also written to
supply-alert-<date>.json beside the run).

These tests pin the grading helper, and publish_date's accounting
across the fresh-publish shape of the incident (unpublished race,
no extras, past the deadline), the normal extras-present day, and
frozen races standing on mixed lanes.
"""
from __future__ import annotations

import io
import json
import os
import tempfile
import urllib.parse
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch
from zoneinfo import ZoneInfo

from rewrite.output.api_shape import MODEL_VERSION
from scripts.arvexq_rewrite_publish import (
    _marker_lane, _supply_report, publish_date)

JST = ZoneInfo("Asia/Tokyo")
DATE = "2099-01-01"
POST = "20:50"
FIXED_NOW = datetime(2099, 1, 1, 10, 0, tzinfo=JST)
RACE_ID = "nar-2099-01-01-高知-01"
NAMES = {1: "アアア", 2: "イイイ", 3: "ウウウ", 4: "エエエ", 5: "オオオ"}
ODDS = {1: 2.4, 2: 3.1, 3: 5.5, 4: 9.0, 5: 21.0}
RECEIPT = "a" * 64


class _FixedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return FIXED_NOW


def past_run(day: str, finish: int, *, distance=1400) -> dict:
    return {
        "date": day, "track": "高知", "raceNumber": 3,
        "distance": distance, "surface": "ダート", "condition": "良",
        "finish": finish, "fieldSize": 10, "timeSeconds": 92.0 + finish,
        "last3fSeconds": 38.0, "cornerPositions": [3, 3, 2],
        "carriedWeight": 55, "jockey": "騎手", "winOdds": 4.0,
        "bodyWeight": 470, "marginSeconds": 0.4,
    }


def fresh_detail() -> dict:
    """A never-published pre-off detail, as fetched from the API."""
    horses = []
    for number in (1, 2, 3, 4, 5):
        horses.append({
            "horseNumber": number, "name": NAMES[number],
            "frameNumber": number, "age": 4, "sex": "牡",
            "carriedWeight": 55.0, "jockey": "騎手", "trainer": "調教師",
            "winOdds": ODDS[number], "popularity": number,
            "allPastRuns": [
                past_run("2098-12-20", number),
                past_run("2098-12-06", (number % 5) + 1),
                past_run("2098-11-15", ((number + 1) % 5) + 1,
                         distance=1500),
            ],
        })
    return {
        "id": RACE_ID, "date": DATE, "circuit": "地方", "track": "高知",
        "raceNumber": 1, "scheduledStartTime": POST,
        "distance": 1500, "surface": "ダート", "condition": "良",
        "horses": horses,
    }


def frozen_detail(race_id: str, lane: str) -> dict:
    """An already-published detail standing frozen on ``lane``."""
    return {
        "id": race_id,
        "date": DATE,
        "track": "高知",
        "scheduledStartTime": POST,
        "predictionStatus": "ready",
        "predictionModelVersion": MODEL_VERSION,
        "preparedMeta": {"rewritePublish": {
            "modelVersion": MODEL_VERSION,
            "publishedAt": "2099-01-01T08:00:00+09:00",
            "receiptSha256": RECEIPT,
            "abilityLane": lane}},
        "unifiedForecast": {
            "receiptSha256": RECEIPT,
            "roster": [{"horseNumber": 1, "name": "アアア"},
                       {"horseNumber": 2, "name": "イイイ"},
                       {"horseNumber": 3, "name": "ウウウ"}]},
        "horses": [{"horseNumber": 1, "name": "アアア"},
                   {"horseNumber": 2, "name": "イイイ"},
                   {"horseNumber": 3, "name": "ウウウ"}],
    }


EXTRAS = {RACE_ID: {"segment": "nar",
                    "extras": {str(n): {"elo": 1500.0} for n in NAMES}}}


def run_publish(details: dict, extras: dict):
    """publish_date (dry-run) over a fake API serving ``details``.

    Returns (counts, stdout, cwd) with the alert file, if any, left
    in the returned temp directory for inspection.
    """
    summaries = [{"race_id": rid, "id": rid, "track": "高知"}
                 for rid in details]

    def fake_get(url: str):
        if url.startswith("/api/races"):
            return {"races": summaries}
        rid = urllib.parse.unquote(url.rsplit("/", 1)[-1])
        return {"detail": details[rid]}

    tmp = tempfile.TemporaryDirectory()
    stdout = io.StringIO()
    cwd = os.getcwd()
    os.chdir(tmp.name)
    try:
        with patch("scripts.arvexq_rewrite_publish._get",
                   side_effect=fake_get), \
                patch("scripts.arvexq_rewrite_publish._load_protect",
                      return_value=lambda old, new: new), \
                patch("scripts.arvexq_rewrite_publish._load_v8_extras",
                      return_value=extras), \
                patch("scripts.arvexq_rewrite_publish.datetime",
                      _FixedDateTime), \
                redirect_stdout(stdout):
            counts = publish_date(DATE, None, True)
    finally:
        os.chdir(cwd)
    return counts, stdout.getvalue(), tmp


class MarkerLaneTests(TestCase):
    def test_reads_ability_lane(self):
        detail = {"preparedMeta": {"rewritePublish": {
            "abilityLane": "v1-prior"}}}
        self.assertEqual(_marker_lane(detail), "v1-prior")

    def test_unreadable_details_have_no_lane(self):
        self.assertIsNone(_marker_lane({}))
        self.assertIsNone(_marker_lane({"preparedMeta": {}}))
        self.assertIsNone(_marker_lane(
            {"preparedMeta": {"rewritePublish": {}}}))
        self.assertIsNone(_marker_lane(None))
        self.assertIsNone(_marker_lane("nope"))


class SupplyReportTests(TestCase):
    def test_no_races_no_fallback(self):
        report = _supply_report(DATE, {}, {}, FIXED_NOW)
        self.assertEqual(report["scope"], "none")
        self.assertIsNone(report["alert"])

    def test_top_lane_only_is_none(self):
        standing = {"r1": "v9b-cal-market", "r2": "v8-elo-speed2"}
        report = _supply_report(DATE, standing, {}, FIXED_NOW)
        self.assertEqual(report["scope"], "none")
        self.assertEqual(report["fallbackIds"], [])

    def test_partial_fallback_is_distinguished(self):
        standing = {"r1": "v1-prior", "r2": "v9b-cal-market"}
        report = _supply_report(DATE, standing, {"r2": {}}, FIXED_NOW)
        self.assertEqual(report["scope"], "partial")
        self.assertEqual(report["fallbackIds"], ["r1"])
        self.assertTrue(report["extrasPresent"])
        self.assertIsNone(report["alert"])

    def test_all_fallback_extras_missing_alerts(self):
        standing = {"r1": "v1-prior", "r2": "v1-prior"}
        report = _supply_report(DATE, standing, {}, FIXED_NOW)
        self.assertEqual(report["scope"], "all")
        self.assertFalse(report["extrasPresent"])
        alert = report["alert"]
        self.assertIn("ALL 2 SERVED RACES ON THE V1 FALLBACK",
                      alert["shout"])
        self.assertIn("V8 EXTRAS FILE MISSING", alert["shout"])
        payload = alert["payload"]
        self.assertEqual(payload["kind"], "arvexq-supply-alert")
        self.assertEqual(payload["date"], DATE)
        self.assertEqual(payload["scope"], "all")
        self.assertEqual(payload["servedRaces"], 2)
        self.assertEqual(payload["v1FallbackRaces"], 2)
        self.assertEqual(payload["fallbackRaceIds"], ["r1", "r2"])
        self.assertFalse(payload["extrasFilePresent"])
        self.assertIn("missing or unreadable", payload["message"])

    def test_all_fallback_extras_present_names_other_cause(self):
        standing = {"r1": "v1-prior"}
        extras = {"r1": {"segment": "nar", "extras": {"1": {}}}}
        report = _supply_report(DATE, standing, extras, FIXED_NOW)
        self.assertEqual(report["scope"], "all")
        self.assertTrue(report["extrasPresent"])
        self.assertIn("was not usable", report["alert"]["payload"]
                      ["message"])


class PublishSupplyAlertTests(TestCase):
    def test_fresh_publish_without_extras_alerts(self):
        # The 2026-11-12 shape: unpublished race, extras file
        # missing, deadline passed -> published on v1, loudly.
        counts, out, tmp = run_publish({RACE_ID: fresh_detail()}, {})
        with tmp:
            self.assertEqual(counts["published"], 1)
            self.assertEqual(counts["v1Fallback"], 1)
            self.assertFalse(counts["extrasPresent"])
            self.assertEqual(counts["supplyAlert"], "all")
            self.assertIn("SUPPLY ALERT", out)
            self.assertIn("ALL 1 SERVED RACES ON THE V1 FALLBACK",
                          out)
            alert_file = Path(tmp.name) / f"supply-alert-{DATE}.json"
            self.assertTrue(alert_file.exists())
            payload = json.loads(
                alert_file.read_text(encoding="utf-8"))
            self.assertEqual(payload["fallbackRaceIds"], [RACE_ID])
            self.assertEqual(payload["servedRaces"], 1)
            self.assertFalse(payload["extrasFilePresent"])

    def test_fresh_publish_with_extras_is_quiet(self):
        counts, out, tmp = run_publish(
            {RACE_ID: fresh_detail()}, EXTRAS)
        with tmp:
            self.assertEqual(counts["published"], 1)
            self.assertEqual(counts["v1Fallback"], 0)
            self.assertTrue(counts["extrasPresent"])
            self.assertEqual(counts["supplyAlert"], "none")
            self.assertNotIn("SUPPLY ALERT", out)
            self.assertNotIn("SUPPLY WARNING", out)
            self.assertFalse(
                (Path(tmp.name) / f"supply-alert-{DATE}.json")
                .exists())

    def test_frozen_mix_warns_partial_without_alert_file(self):
        v1_id = "nar-2099-01-01-高知-11"
        v8_id = "nar-2099-01-01-高知-12"
        counts, out, tmp = run_publish(
            {v1_id: frozen_detail(v1_id, "v1-prior"),
             v8_id: frozen_detail(v8_id, "v8-elo-speed2")}, {})
        with tmp:
            self.assertEqual(counts["frozen"], 2)
            self.assertEqual(counts["v1Fallback"], 1)
            self.assertEqual(counts["supplyAlert"], "partial")
            self.assertIn("SUPPLY WARNING", out)
            self.assertIn(v1_id, out)
            self.assertNotIn("SUPPLY ALERT", out)
            self.assertFalse(
                (Path(tmp.name) / f"supply-alert-{DATE}.json")
                .exists())

    def test_frozen_all_v1_alerts(self):
        v1a = "nar-2099-01-01-高知-11"
        v1b = "nar-2099-01-01-高知-12"
        counts, out, tmp = run_publish(
            {v1a: frozen_detail(v1a, "v1-prior"),
             v1b: frozen_detail(v1b, "v1-prior")}, {})
        with tmp:
            self.assertEqual(counts["frozen"], 2)
            self.assertEqual(counts["v1Fallback"], 2)
            self.assertEqual(counts["supplyAlert"], "all")
            self.assertIn("SUPPLY ALERT", out)
            payload = json.loads(
                (Path(tmp.name) / f"supply-alert-{DATE}.json")
                .read_text(encoding="utf-8"))
            self.assertEqual(payload["fallbackRaceIds"], [v1a, v1b])


if __name__ == "__main__":
    import unittest
    unittest.main()
