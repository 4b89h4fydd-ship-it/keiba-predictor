"""Tests for the rewrite data foundation (offline, synthetic fixtures)."""
import json
import tempfile
import unittest
from pathlib import Path

from rewrite.data.normalize import normalize_race
from rewrite.data.quality import day_quality, race_quality
from rewrite.data.sources import RawPayload, SourceUnavailable
from rewrite.data.store import Store
from rewrite.safety.contracts import Segment
from datetime import datetime, timezone


def summary(**overrides):
    base = {
        "race_id": "nar-2026-10-28-名古屋-01",
        "race_date": "2026-10-28",
        "circuit": "地方",
        "track": "名古屋",
        "race_no": 1,
        "start_time": "12:20",
        "title": "Ｃ１７組",
        "surface": "",
        "distance": 1500,
        "weather": "不明",
        "condition": "不明",
        "updated_at": 0,
    }
    base.update(overrides)
    return base


def horse(number, **overrides):
    base = {
        "horseNumber": number,
        "id": f"h{number}",
        "name": f"テスト{number}",
        "frameNumber": number,
        "age": 4,
        "sex": "牡",
        "jockey": "騎手",
        "trainer": "調教師",
        "carriedWeight": 56.0,
        "bodyWeight": 480,
        "bodyWeightChange": 2,
        "winOdds": 5.0,
        "scratched": False,
        "allPastRuns": [
            {"date": "2026-10-01", "track": "名古屋", "distance": 1500,
             "surface": "ダート", "finish": 2, "fieldSize": 10,
             "cornerPositions": [3, 3, 2, 2], "marginText": "クビ",
             "timeSeconds": 98.1, "jockey": "騎手"}
        ],
    }
    base.update(overrides)
    return base


def detail(horses):
    return {"horses": horses}


class NormalizeTests(unittest.TestCase):
    def test_unknowns_stay_unknown(self):
        race = normalize_race(summary(), detail([horse(1), horse(2)]), "test://x")
        self.assertIsNone(race.surface.value)
        self.assertEqual(race.surface.missing_reason, "empty_string")
        self.assertIsNone(race.weather.value)
        self.assertTrue(race.weather.missing_reason.startswith("unknown_literal"))
        self.assertIsNone(race.updated_at.value)
        self.assertEqual(race.updated_at.missing_reason, "zero_or_null_timestamp")
        self.assertEqual(race.segment, Segment.NAR)

    def test_banei_rejected(self):
        with self.assertRaises(ValueError):
            normalize_race(summary(track="帯広"), detail([horse(1)]), "test://x")

    def test_future_runs_rejected_and_counted(self):
        future = {"date": "2026-10-28", "finish": 1, "fieldSize": 9}
        runner = normalize_race(
            summary(), detail([horse(1, allPastRuns=[future]), horse(2)]), "test://x"
        ).runners[0]
        self.assertEqual(runner.past_runs, ())
        self.assertEqual(runner.rejected_future_runs, 1)

    def test_segments(self):
        jra = normalize_race(
            summary(circuit="中央", track="東京", title="2歳新馬"), detail([horse(1)]), "t"
        )
        self.assertEqual(jra.segment, Segment.DEBUT)
        nar_debut = normalize_race(
            summary(title="ＮｅｗＢｅｇｉｎｎｉｎｇ ２歳初出走"),
            detail([horse(1, allPastRuns=[]), horse(2, allPastRuns=[])]), "t",
        )
        self.assertEqual(nar_debut.segment, Segment.DEBUT)
        self.assertTrue(race_quality(nar_debut).eligible)
        jumps = normalize_race(
            summary(circuit="中央", track="中山", title="障害3歳以上未勝利"), detail([horse(1)]), "t"
        )
        self.assertEqual(jumps.segment, Segment.JUMPS)


class QualityTests(unittest.TestCase):
    def test_quality_rates_and_gate(self):
        race = normalize_race(
            summary(), detail([horse(1, winOdds=None), horse(2)]), "test://x"
        )
        q = race_quality(race)
        self.assertTrue(q.eligible)
        self.assertEqual(q.field_coverage["win_odds"], 0.5)
        report = day_quality([race])
        self.assertEqual(report["runner_field_missing_rate"]["win_odds"], 0.5)
        self.assertEqual(report["race_field_missing_rate"]["weather"], 1.0)

    def test_no_past_runs_blocks_non_debut(self):
        race = normalize_race(
            summary(), detail([horse(1, allPastRuns=[]), horse(2, allPastRuns=[])]), "t"
        )
        q = race_quality(race)
        self.assertFalse(q.eligible)
        self.assertIn("no_runner_has_past_runs", q.blocking_reasons)


class StoreTests(unittest.TestCase):
    def test_raw_first_write_wins_and_verifies(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / "t.sqlite3")
            payload = RawPayload(
                kind="api_races", source_url="test://x",
                fetched_at=datetime.now(timezone.utc), body=b'{"a": 1}',
            )
            digest, inserted = store.save_raw(payload, "date:2026-10-28")
            self.assertTrue(inserted)
            _, inserted_again = store.save_raw(payload, "date:2026-10-28")
            self.assertFalse(inserted_again)
            self.assertTrue(store.verify_raw("api_races", "date:2026-10-28", digest))
            store.close()

    def test_non_json_payload_raises(self):
        payload = RawPayload(
            kind="static_racecards", source_url="test://x",
            fetched_at=datetime.now(timezone.utc), body=b"<html>spa</html>",
        )
        with self.assertRaises(SourceUnavailable):
            payload.json()
        self.assertEqual(json.loads(b'{"ok": true}'), {"ok": True})


if __name__ == "__main__":
    unittest.main()
