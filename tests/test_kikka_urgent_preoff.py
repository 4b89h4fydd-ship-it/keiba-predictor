"""Emergency Kyoto G1 is race-specific, JRA-observed and never backdated."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from hashlib import sha256
import json
from unittest import TestCase
from unittest.mock import patch

from arvexq.forecast.publication import public_race
from arvexq.prediction.kikka_urgent import (
    EXPECTED, RACE_DATE, RACE_ID, VERSION, LEARNED_VERSION,
    verified_entry, overlay_preserving_facts, candidate_marks,
)
from arvexq.prediction.prerace_archive import JST
from scripts.arvexq_kikka_urgent import training_races

PRE = datetime.fromisoformat("2026-10-25T14:20:00+09:00")
AFTER = datetime.fromisoformat("2026-10-25T15:41:00+09:00")


def facts():
    row = {
        "id": RACE_ID, "date": RACE_DATE, "circuit": "中央", "track": "京都",
        "raceNumber": 11, "title": "菊花賞", "distance": 3000,
        "surface": "芝", "startTime": "15:40", "scheduledStartTime": "15:40",
        "horses": [{"horseNumber": i, "name": name, "recentRaces": [
            {"date": "2026-10-10", "track": "阪神", "finish": i,
             "fieldSize": 18}]} for i, name in enumerate(EXPECTED, 1)]
    }
    return row


def candidate(detail, *, stamped="2026-10-25T14:20:00+09:00", marks=None):
    marks = marks if marks is not None else [
        {"horseNumber": 8, "mark": "◎"},
        {"horseNumber": 10, "mark": "○"},
        {"horseNumber": 9, "mark": "▲"},
        {"horseNumber": 5, "mark": "△"},
        {"horseNumber": 6, "mark": "☆"},
    ]
    # Deliberately chosen only for a projection-contract fixture; not real
    # forecast picks. No fixture is deployed or used for a wager.
    normalized = sorted((m["horseNumber"], m["mark"]) for m in marks)
    model_hash = "a" * 64
    digest = sha256(json.dumps({
        "raceId": RACE_ID, "roster": EXPECTED,
        "modelHash": model_hash, "marks": normalized
    }, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
    return {"version": VERSION, "raceId": RACE_ID, "raceDate": RACE_DATE,
            "capturedAt": stamped, "trainedThrough": "2026-10-24",
            "modelVersion": LEARNED_VERSION, "modelHash": model_hash,
            "sourceHash": digest, "provisional": True,
            "productionEligible": False, "bettingRecommended": False,
            "marks": [{"horseNumber": row["horseNumber"], "markSymbol": row["mark"]} for row in marks],
            "probabilityCalibration": "unverified"}


class KikukaPreoffTests(TestCase):
    def test_only_exact_official_card_passes_before_off(self):
        row = facts()
        verified_entry(row, deepcopy(row), PRE)
        with self.assertRaisesRegex(ValueError, "15:40"):
            verified_entry(row, deepcopy(row), AFTER)
        altered = deepcopy(row)
        altered["horses"][7]["name"] = "間違った馬"
        with self.assertRaisesRegex(ValueError, "18-runner"):
            verified_entry(altered, row, PRE)
        altered = deepcopy(row)
        altered["result"] = {"status": "確定", "finishers": [1, 2]}
        with self.assertRaisesRegex(ValueError, "result"):
            verified_entry(altered, row, PRE)

    def test_unconfirmed_placeholder_is_not_a_result(self):
        row = facts()
        row["result"] = {"status": "未確定", "finishers": [], "payouts": {}}
        verified_entry(row, deepcopy(row), PRE)

    def test_candidate_public_projection_is_not_a_bet_or_stage64(self):
        race = facts()
        race["kikkaCandidate"] = candidate(race)
        original = deepcopy(race)
        with patch("arvexq.forecast.publication.build_prediction",
                   side_effect=AssertionError("Stage64 never allowed for this race")):
            published = public_race(race)
        self.assertEqual(published["predictionStatus"], "candidate-analysis")
        self.assertEqual([r["mark"] for r in published["predictionMarks"]
                          if r["horseNumber"] == 8], ["◎"])
        self.assertEqual(published["recommendedBets"], [])
        self.assertFalse(published["prediction"]["productionEligible"])
        self.assertNotIn("kikkaCandidate", published.get("prediction") or {})
        self.assertEqual(race, original)

    def test_tampered_and_postoff_mark_claims_are_rejected(self):
        row = facts()
        bad = candidate(row)
        bad["marks"][0]["horseNumber"] = 4
        row["kikkaCandidate"] = bad
        self.assertIsNone(candidate_marks(row))
        row["kikkaCandidate"] = candidate(row, stamped="2026-10-25T15:42:00+09:00")
        self.assertIsNone(candidate_marks(row))
        row["kikkaCandidate"] = candidate(row, marks=[
            {"horseNumber": 8, "mark": "◎"}, {"horseNumber": 10, "mark": "◎"}])
        self.assertIsNone(candidate_marks(row))
        row["kikkaCandidate"] = candidate(row)
        row["kikkaCandidate"]["bettingRecommended"] = True
        self.assertIsNone(candidate_marks(row))

    def test_existing_archives_are_not_overwritten(self):
        row = facts()
        row["preRacePrediction"] = {"fixedAt": "2026-10-25T08:00:00+09:00"}
        with self.assertRaisesRegex(ValueError, "immutable"):
            overlay_preserving_facts(row, row, row, candidate(row), PRE)

    def test_live_sync_preserves_first_and_subsequent_kikka_seals(self):
        from scripts.arvexq_protect_sync import protect_detail
        previous = facts()
        initial = deepcopy(previous)
        initial['kikkaCandidate'] = candidate(previous)
        first = protect_detail(previous, initial)
        self.assertEqual(candidate_marks(first),
                         [{"horseNumber": x["horseNumber"], "mark": x["markSymbol"]}
                          for x in sorted(initial['kikkaCandidate']['marks'], key=lambda row: row['horseNumber'])])
        later = deepcopy(first)
        later.pop('kikkaCandidate')
        later['oddsUpdatedAt'] = 'new-market'
        saved = protect_detail(first, later)
        self.assertEqual(saved['kikkaCandidate'], first['kikkaCandidate'])
        forged = deepcopy(saved)
        forged['kikkaCandidate'] = candidate(previous, stamped='2026-10-25T15:41:00+09:00')
        again = protect_detail(saved, forged)
        self.assertEqual(again['kikkaCandidate'], first['kikkaCandidate'])

    def test_repair_missing_mark_field_only_when_hash_matches(self):
        from scripts.arvexq_protect_sync import protect_detail
        old = facts()
        damaged = candidate(old)
        damaged['marks'] = [{'horseNumber': row['horseNumber']} for row in damaged['marks']]
        old['kikkaCandidate'] = damaged
        updated = deepcopy(old)
        updated['kikkaCandidate'] = candidate(old, stamped='2026-10-25T14:25:00+09:00')
        with patch('arvexq.pipeline.persisted_inputs.may_create_prerace_prediction', return_value=True):
            restored = protect_detail(old, updated)
        self.assertEqual(restored['kikkaCandidate']['capturedAt'], damaged['capturedAt'])
        self.assertIsNotNone(candidate_marks(restored))
        forged = deepcopy(updated)
        forged['kikkaCandidate']['sourceHash'] = '0'*64
        with patch('arvexq.pipeline.persisted_inputs.may_create_prerace_prediction', return_value=True):
            retained = protect_detail(old, forged)
        self.assertEqual(retained['kikkaCandidate'], damaged)

    def test_earlier_only_jra_training_sources(self):
        import scripts.arvexq_kikka_urgent as urgent
        mock_races = [
            {"id": "jra-2026-10-24-京都-01", "date": "2026-10-24", "circuit": "中央"},
            {"id": "nar-2026-10-24-帯広ば-01", "date": "2026-10-24", "circuit": "地方"},
        ]
        race = facts()
        race["id"], race["date"] = mock_races[0]["id"], "2026-10-24"
        race["result"] = {"status": "確定", "finishers": []}
        with patch.object(urgent, "day_summary", return_value=mock_races), \
             patch.object(urgent, "race_detail", return_value=race) as got:
            rows, errors = training_races("https://example.invalid",
                                           dates=("2026-10-24",))
        self.assertEqual(len(rows), 1)
        self.assertEqual(got.call_count, 1)
