"""Official-only course revision and immutable morning mark regression."""
import io
import json
import os
import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

from arvexq.prediction.official_course_revision import (
    JST, official_event, meaningful_change, pre_off_change, latest_pre_off_marks,
)
from arvexq.ingest.official_course_feeds import fetch_course_events
from scripts.arvexq_live_sync import apply_official_mark_revision
from scripts.arvexq_protect_sync import protect_detail


def observation(going="良", minute="08:00", *, date="2026-10-10", source="https://www.jra.go.jp/keiba/baba/"):
    return {
        "sourceKind": "official_course_condition", "sourceUrl": source,
        "raceDate": date, "track": "東京", "surface": "芝",
        "publishedAt": date + "T" + minute + ":00+09:00", "going": going,
        "cushionValue": 9.2, "moisturePercent": 11.3,
    }


def race():
    original = [
        {"horseNumber": 1, "mark": "◎"},
        {"horseNumber": 2, "mark": "○"},
        {"horseNumber": 3, "mark": "▲"},
    ]
    return {
        "id": "jra-2026-10-10-東京-01",
        "date": "2026-10-10", "track": "東京", "circuit": "中央", "surface": "芝",
        "condition": "良", "startTime": "10:00", "officialCourseCondition": observation(),
        "morningMarkSnapshot": {
            "version": "arvexq-morning-marks-v1", "raceId": "jra-2026-10-10-東京-01",
            "raceDate": "2026-10-10", "fixedAt": "2026-10-10T07:00:00+09:00",
            "originalCondition": "良", "horses": original,
        },
    }


class OfficialRevisionTests(unittest.TestCase):
    def test_reject_unofficial_bias_or_uncited_observation(self):
        self.assertIsNone(official_event(observation(source="https://netkeiba.com/")))
        self.assertIsNone(official_event({"sourceKind": "ai_bias", **{"going": "良"}}))
        self.assertIsNone(official_event({**observation(), "publishedAt": "not-a-time"}))
        self.assertIsNone(official_event({**observation(), "moisturePercent": 999}))
        self.assertEqual(official_event(observation())["going"], "良")

    def test_only_material_official_change_before_post(self):
        before = observation()
        after = observation("稍重", "09:00")
        now = datetime(2026, 10, 10, 9, 15, tzinfo=JST)
        self.assertIn("良→稍重", pre_off_change(race(), before, after, now))
        self.assertEqual(pre_off_change(race(), before, after, datetime(2026, 10, 10, 10, 0, tzinfo=JST)), "")
        self.assertEqual(pre_off_change(race(), before, {**after, "track": "京都"}, now), "")
        self.assertEqual(pre_off_change(race(), before, observation("良", "09:00"), now), "")
        self.assertEqual(pre_off_change(race(), before, {**after, "sourceUrl": "https://nonofficial.example/"}, now), "")
        self.assertEqual(pre_off_change(race(), before, {**after, "publishedAt": "2026-10-10T10:01:00+09:00"}, now), "")

    def test_provenance_limited_preoff_history(self):
        d = race()
        valid = {
            "version": "arvexq-official-mark-revision-v1", "raceId": d["id"],
            "raceDate": d["date"], "revisedAt": "2026-10-10T09:10:00+09:00",
            "officialCourseCondition": observation("稍重", "09:00"),
            "reason": "公式馬場状態変更", "horses": [
                {"horseNumber": 1, "mark": "○"},
                {"horseNumber": 2, "mark": "◎"},
                {"horseNumber": 3, "mark": "▲"},
            ],
        }
        d["officialMarkRevisions"] = [valid]
        self.assertEqual(latest_pre_off_marks(d)["horses"][1]["mark"], "◎")
        d["officialMarkRevisions"] = [{**valid, "revisedAt": "2026-10-10T10:01:00+09:00"}]
        self.assertEqual(latest_pre_off_marks(d)["horses"][0]["mark"], "◎")
        d["officialMarkRevisions"] = [{**valid, "officialCourseCondition": observation("稍重", "09:00", source="https://fake.local/")}]
        self.assertEqual(latest_pre_off_marks(d)["horses"][0]["mark"], "◎")

    def test_live_sync_revises_once_and_preserves_original(self):
        baseline = race()
        candidate = {**baseline, "condition": "稍重",
                     "officialCourseCondition": observation("稍重", "09:00")}
        returns = SimpleNamespace(returncode=0, stdout=json.dumps({"horses": [
            {"horseNumber": 1, "mark": "○"},
            {"horseNumber": 2, "mark": "◎"},
            {"horseNumber": 3, "mark": "▲"},
        ]}), stderr="")
        now = datetime(2026, 10, 10, 9, 15, tzinfo=JST)
        with patch("subprocess.run", return_value=returns) as mocked:
            output, reason = apply_official_mark_revision(baseline, candidate, now)
        mocked.assert_called_once()
        self.assertIn("良→稍重", reason)
        self.assertEqual(output["morningMarkSnapshot"]["horses"][0]["mark"], "◎")
        self.assertEqual(output["officialMarkRevisions"][0]["horses"][1]["mark"], "◎")
        self.assertEqual(protect_detail(output, {**candidate, "officialMarkRevisions": []})["officialMarkRevisions"],
                         output["officialMarkRevisions"])
        revised, reason = apply_official_mark_revision(output, output, now)
        self.assertFalse(reason)
        self.assertEqual(len(revised["officialMarkRevisions"]), 1)
        after, reason = apply_official_mark_revision(baseline, candidate,
            datetime(2026, 10, 10, 10, 1, tzinfo=JST))
        self.assertFalse(reason)
        self.assertEqual(after.get("officialMarkRevisions"), None)

    def test_authorized_feed_poll_requires_connected_token(self):
        rows = [race()]
        now = datetime(2026, 10, 10, 9, 15, tzinfo=JST)
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(fetch_course_events("2026-10-10", rows, now=now), {})
        with patch.dict(os.environ, {
            "ARVEXQ_OFFICIAL_COURSE_FEED_URL": "https://authorized.example/api/course",
            "ARVEXQ_OFFICIAL_COURSE_FEED_TOKEN": "test-token",
        }):
            response = io.BytesIO(json.dumps({"events": [observation("稍重", "09:00")]}).encode())
            with patch("urllib.request.urlopen", return_value=response):
                matched = fetch_course_events("2026-10-10", rows, now=now)
        self.assertIn(rows[0]["id"], matched)


if __name__ == "__main__":
    unittest.main()
