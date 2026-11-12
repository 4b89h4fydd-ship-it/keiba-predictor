"""Mass-feature archive co-publication (2026-11-11).

The rewrite publish lane is the sole forecast producer, but it never
carried the preRacePrediction lock the legacy persistence path keyed
on, so no published detail has carried massFeatureArchive since
2026-10-17 — while v9b publications only exist from 2026-11-04. The
sealed-forecast x feature-archive intersection was therefore empty
and no same-race model comparison could be graded.

build_publish_detail now freezes the pre-off feature matrix from the
same input detail it computes the forecast from and attaches the
transport archive to the same published detail. These tests pin:
the archive is present, genuinely origin-verified (the export-side
check the MotherDuck frozen-ranking export applies), restorable,
receipt-verifiable, preserved by the protect round-trip — and that
a feature-build failure never blocks publication, only gets stamped.
"""
from __future__ import annotations

from datetime import datetime
from unittest import TestCase
from unittest.mock import patch
from zoneinfo import ZoneInfo

from arvexq.prediction.mass_feature_transport import (
    SCHEME, restore_snapshot)
from arvexq.prediction.unified_product import verified as verified_unified
from rewrite.analysis.forecast import RaceForecast, RunnerForecast
from rewrite.data.normalize import Obs, RaceRecord, RunnerRecord, obs
from rewrite.output.api_shape import MODEL_VERSION
from rewrite.safety.contracts import Segment
from scripts.arvexq_protect_sync import protect_detail
from scripts.arvexq_rewrite_publish import (
    _build_mass_feature_archive, build_publish_detail)
from scripts.export_motherduck_frozen_ranking import transform_item

JST = ZoneInfo("Asia/Tokyo")
RACE_ID = "nar-2026-11-04-金沢-01"
DATE = "2026-11-04"
POST = "12:50"
NOW = datetime(2026, 11, 4, 10, 5, tzinfo=JST)  # 165 min before post
NAMES = {1: "アアア", 2: "イイイ", 3: "ウウウ", 4: "エエエ", 5: "オオオ"}
ODDS = {1: 2.4, 2: 3.1, 3: 5.5, 4: 9.0, 5: 21.0}
STRENGTHS = {1: 0.30, 2: 0.25, 3: 0.20, 4: 0.15, 5: 0.10}


def past_run(day: str, finish: int, *, distance=1400) -> dict:
    return {
        "date": day, "track": "金沢", "raceNumber": 3,
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
                past_run("2026-10-20", number),
                past_run("2026-10-06", (number % 5) + 1),
                past_run("2026-09-15", ((number + 1) % 5) + 1,
                         distance=1500),
            ],
        })
    return {
        "id": RACE_ID, "date": DATE, "circuit": "地方", "track": "金沢",
        "raceNumber": 1, "scheduledStartTime": POST,
        "distance": 1500, "surface": "ダート", "condition": "良",
        "horses": horses,
    }


def fabricated_race() -> RaceRecord:
    missing = Obs(None, "test", "not_captured")
    runners = []
    for number in (1, 2, 3, 4, 5):
        runners.append(RunnerRecord(
            number=number, horse_id=missing,
            name=obs(NAMES[number], "test"), frame_number=missing,
            age=missing, sex=missing, jockey=missing, trainer=missing,
            carried_weight=missing, body_weight=missing,
            body_weight_change=missing,
            win_odds=obs(ODDS[number], "test"),
            scratched=False, past_runs=()))
    return RaceRecord(
        race_id=RACE_ID, date=DATE, circuit=obs("地方", "test"),
        track="金沢", race_number=obs(1, "test"), title=missing,
        start_time=obs(POST, "test"), distance=obs(1500, "test"),
        surface=obs("ダート", "test"), weather=missing,
        condition=missing, updated_at=missing, segment=Segment.NAR,
        source="test", runners=tuple(runners))


def v8_forecast() -> RaceForecast:
    runners = [RunnerForecast(
        number=n, name=NAMES[n], ability_score=0.5, strength=s,
        pace_adjustment=1.0, pace_reasons=(), p_win=None, p_top2=None,
        p_top3=None, mark="", status="scored")
        for n, s in STRENGTHS.items()]
    return RaceForecast(RACE_ID, 3.0, "uncalibrated-prior",
                        tuple(runners), "ok")


EXTRAS = {RACE_ID: {"segment": "nar",
                    "extras": {str(n): {"elo": 1500.0} for n in NAMES}}}


def build(detail=None):
    with patch("scripts.arvexq_rewrite_publish.normalize_race",
               return_value=fabricated_race()), \
            patch("scripts.arvexq_rewrite_publish.forecast_race_v8",
                  return_value=v8_forecast()), \
            patch("scripts.arvexq_rewrite_publish._load_v8_extras",
                  return_value=EXTRAS):
        return build_publish_detail(
            detail if detail is not None else fresh_detail(),
            {"race_id": RACE_ID, "id": RACE_ID}, NOW)


class MassFeatureArchiveHelperTests(TestCase):
    def test_helper_builds_genuinely_verified_archive(self):
        archive, status = _build_mass_feature_archive(fresh_detail())
        self.assertIsNotNone(archive, status)
        self.assertEqual(status["status"], "attached")
        self.assertEqual(archive["encoding"], SCHEME)
        self.assertIs(archive["originHashVerified"], True)
        self.assertEqual(archive["originStatus"], "verified")
        self.assertEqual(archive["raceId"], RACE_ID)
        self.assertEqual(archive["raceDate"], DATE)
        self.assertEqual(archive["horseCount"], 5)
        snapshot = restore_snapshot(archive, race_id=RACE_ID,
                                    race_date=DATE)
        self.assertEqual(snapshot["featureHash"],
                         archive["featureHash"])
        self.assertEqual(len(snapshot["rows"]), 5)
        self.assertTrue(all(row["features"] for row in snapshot["rows"]))

    def test_helper_excludes_banei(self):
        detail = fresh_detail()
        detail["track"] = "帯広"
        detail["id"] = "nar-2026-11-04-帯広-01"
        archive, status = _build_mass_feature_archive(detail)
        self.assertIsNone(archive)
        self.assertEqual(status["status"], "excluded-banei")

    def test_helper_failure_is_returned_not_raised(self):
        with patch("arvexq.prediction.mass_feature_snapshot"
                   ".build_mass_feature_snapshot",
                   side_effect=RuntimeError("boom")):
            archive, status = _build_mass_feature_archive(fresh_detail())
        self.assertIsNone(archive)
        self.assertEqual(status["status"], "error")
        self.assertIn("RuntimeError", status["error"])


class MassFeatureArchiveBuildTests(TestCase):
    def test_publication_carries_verified_archive(self):
        detail = fresh_detail()
        new, receipt = build(detail)
        self.assertIsNotNone(new, receipt)
        archive = new.get("massFeatureArchive")
        self.assertIsInstance(archive, dict)
        self.assertIs(archive["originHashVerified"], True)
        self.assertEqual(archive["originStatus"], "verified")
        self.assertEqual(new["massFeatureHash"], archive["featureHash"])
        self.assertTrue(new["massFeatureSchemaVersion"])
        self.assertTrue(new["massFeatureSnapshotVersion"])
        self.assertNotIn("massFeatureSnapshot", new)
        # The forecast itself is untouched by the sidecar: the lane's
        # own self-verify (the PR #519 protected-product gate form)
        # still passes with the archive attached.
        check = verified_unified(dict(
            detail, unifiedForecast=new["unifiedForecast"]))
        self.assertIsNotNone(check)
        self.assertIsNotNone(verified_unified(new))
        # The export-side gate the MotherDuck frozen-ranking export
        # applies: with settled labels the archived rows export.
        settled = dict(new)
        settled["result"] = {
            "status": "確定",
            "finishers": [{"horseNumber": n, "finish": i + 1}
                          for i, n in enumerate((1, 2, 3, 4, 5))],
        }
        rows, status = transform_item(RACE_ID, settled)
        self.assertEqual(status, "exported")
        self.assertEqual(len(rows), 5)
        self.assertTrue(all(
            row["featureHash"] == archive["featureHash"] for row in rows))

    def test_archive_survives_protect_round_trip(self):
        detail = fresh_detail()
        new, receipt = build(detail)
        self.assertIsNotNone(new, receipt)
        protected = protect_detail(detail, new)
        self.assertEqual(protected["massFeatureArchive"],
                         new["massFeatureArchive"])
        self.assertEqual(protected["massFeatureHash"],
                         new["massFeatureHash"])
        self.assertIsNotNone(verified_unified(protected))

    def test_feature_failure_never_blocks_publication(self):
        detail = fresh_detail()
        with patch("arvexq.prediction.mass_feature_snapshot"
                   ".build_mass_feature_snapshot",
                   side_effect=RuntimeError("boom")):
            new, receipt = build(detail)
        self.assertIsNotNone(new, receipt)
        self.assertNotIn("massFeatureArchive", new)
        self.assertEqual(new["predictionModelVersion"], MODEL_VERSION)
        marker = new["preparedMeta"]["rewritePublish"]
        self.assertIn("RuntimeError", marker["massFeatureArchiveError"])
        self.assertIsNotNone(verified_unified(dict(
            detail, unifiedForecast=new["unifiedForecast"])))


if __name__ == "__main__":
    import unittest
    unittest.main()
