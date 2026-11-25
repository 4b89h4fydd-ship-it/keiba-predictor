"""Margin completion from the system's own stored result records.

Runs collected through the newer forward route carry only marginText and
their own timeSeconds, so the observed margin factor stayed unavailable
(2026-11-19: ~37 of 395 horses). complete_detail_margins heals such a run
from the stored detail of that past race: the winner's timeSeconds comes
from the stored finishers, and the gap is written as a measured record
with the honest provenance label "arvexq_result_store". Nothing is ever
estimated from marginText (lengths), and any identity ambiguity or fact
disagreement leaves the run untouched.
"""
from __future__ import annotations

from copy import deepcopy
from unittest import TestCase

from arvexq.prediction.margin_completion import complete_detail_margins
from arvexq.prediction.observed_evidence import attach_model_evidence
from arvexq.prediction.race_intelligence import (
    RESEARCH_EVIDENCE_VERSION,
    attach_evidence,
)
from scripts import arvexq_prefetch as prefetch


def stored_race(rid: str, date: str, track: str, number: int,
                finishers: list[dict]) -> dict:
    return {"id": rid, "date": date, "track": track, "raceNumber": number,
            "circuit": "地方",
            "result": {"status": "確定", "finishers": finishers}}


def target_detail(horses: list[dict]) -> dict:
    return {"id": "nar-2026-11-19-大井-01", "date": "2026-11-19",
            "track": "大井", "circuit": "地方", "distance": 1400,
            "surface": "ダート", "horses": horses}


class MarginCompletionTests(TestCase):
    def setUp(self):
        # Ooi 2026-10-26 3R (2yo maiden, 1400m), as stored by the system.
        self.past = stored_race(
            "nar-2026-10-26-大井-03", "2026-10-26", "大井", 3, [
                {"finish": 1, "horseNumber": 7, "name": "オジャルゴン", "timeSeconds": 89.1},
                {"finish": 5, "horseNumber": 3, "name": "マイライフ", "timeSeconds": 91.4},
                {"finish": 6, "horseNumber": 5, "name": "コーゲンタフボーイ", "timeSeconds": 91.6},
            ])
        self.store = {self.past["id"]: self.past}
        self.day_ids = {"2026-10-26": [self.past["id"]]}

    def fetch_race(self, rid):
        return deepcopy(self.store.get(rid))

    def fetch_day_ids(self, date):
        return list(self.day_ids.get(date) or [])

    def test_completes_via_day_scan_without_race_identity(self):
        horse = {"horseNumber": 7, "name": "コーゲンタフボーイ",
                 "recentRaces": [{"date": "2026-10-26", "track": "大井",
                                  "finish": 6, "fieldSize": 10,
                                  "timeSeconds": 91.6, "marginText": "2.5"}]}
        detail = target_detail([horse])
        stats = complete_detail_margins(detail, self.fetch_race, self.fetch_day_ids)
        run = detail["horses"][0]["recentRaces"][0]
        self.assertEqual(stats["completed"], 1)
        self.assertEqual(run["marginSeconds"], 2.5)
        self.assertEqual(run["timeBehindWinner"], 2.5)
        self.assertEqual(run["marginEvidence"],
                         {"winnerTimeSeconds": 89.1, "horseTimeSeconds": 91.6})
        self.assertEqual(run["marginEvidenceSource"], "arvexq_result_store")
        self.assertEqual(run["raceId"], "nar-2026-10-26-大井-03")
        self.assertEqual(run["raceNumber"], 3)

    def test_completes_via_race_id(self):
        horse = {"horseNumber": 1, "name": "マイライフ",
                 "recentRaces": [{"date": "2026-10-26", "track": "大井",
                                  "raceNumber": 3, "raceId": "nar-2026-10-26-大井-03",
                                  "finish": 5, "fieldSize": 10,
                                  "timeSeconds": 91.4, "marginText": "2.3"}]}
        detail = target_detail([horse])
        stats = complete_detail_margins(detail, self.fetch_race, self.fetch_day_ids)
        run = detail["horses"][0]["recentRaces"][0]
        self.assertEqual(stats["completed"], 1)
        self.assertEqual(run["marginSeconds"], 2.3)

    def test_winner_completes_as_exactly_zero(self):
        horse = {"horseNumber": 2, "name": "オジャルゴン",
                 "recentRaces": [{"date": "2026-10-26", "track": "大井",
                                  "finish": 1, "fieldSize": 10,
                                  "timeSeconds": 89.1, "marginText": ""}]}
        detail = target_detail([horse])
        stats = complete_detail_margins(detail, self.fetch_race, self.fetch_day_ids)
        run = detail["horses"][0]["recentRaces"][0]
        self.assertEqual(stats["completed"], 1)
        self.assertEqual(run["marginSeconds"], 0.0)

    def test_no_completion_when_stored_facts_disagree(self):
        # The stored race has this horse at a different time: the records
        # conflict, so nothing may be written.
        horse = {"horseNumber": 7, "name": "コーゲンタフボーイ",
                 "recentRaces": [{"date": "2026-10-26", "track": "大井",
                                  "finish": 6, "fieldSize": 10,
                                  "timeSeconds": 95.0, "marginText": "2.5"}]}
        detail = target_detail([horse])
        stats = complete_detail_margins(detail, self.fetch_race, self.fetch_day_ids)
        run = detail["horses"][0]["recentRaces"][0]
        self.assertEqual(stats["completed"], 0)
        self.assertEqual(stats["unresolved"], 1)
        self.assertNotIn("marginSeconds", run)

    def test_no_completion_when_race_not_identifiable(self):
        horse = {"horseNumber": 7, "name": "コーゲンタフボーイ",
                 "recentRaces": [{"date": "2026-10-20", "track": "大井",
                                  "finish": 6, "fieldSize": 10,
                                  "timeSeconds": 91.6, "marginText": "2.5"}]}
        detail = target_detail([horse])
        stats = complete_detail_margins(detail, self.fetch_race, self.fetch_day_ids)
        self.assertEqual(stats["completed"], 0)
        self.assertNotIn("marginSeconds", detail["horses"][0]["recentRaces"][0])

    def test_no_completion_when_gap_would_be_negative(self):
        # Own time faster than the stored winner's time: inconsistent
        # records, never a negative margin.
        store = {"nar-2026-10-26-大井-03": stored_race(
            "nar-2026-10-26-大井-03", "2026-10-26", "大井", 3, [
                {"finish": 1, "horseNumber": 7, "name": "オジャルゴン", "timeSeconds": 89.1},
                {"finish": 6, "horseNumber": 5, "name": "コーゲンタフボーイ", "timeSeconds": 88.0},
            ])}
        horse = {"horseNumber": 7, "name": "コーゲンタフボーイ",
                 "recentRaces": [{"date": "2026-10-26", "track": "大井",
                                  "finish": 6, "fieldSize": 10,
                                  "timeSeconds": 88.0, "marginText": "2.5"}]}
        detail = target_detail([horse])
        stats = complete_detail_margins(
            detail, lambda rid: deepcopy(store.get(rid)), self.fetch_day_ids)
        self.assertEqual(stats["completed"], 0)
        self.assertNotIn("marginSeconds", detail["horses"][0]["recentRaces"][0])

    def test_no_completion_without_winner_time(self):
        store = {"nar-2026-10-26-大井-03": stored_race(
            "nar-2026-10-26-大井-03", "2026-10-26", "大井", 3, [
                {"finish": 1, "horseNumber": 7, "name": "オジャルゴン"},
                {"finish": 6, "horseNumber": 5, "name": "コーゲンタフボーイ", "timeSeconds": 91.6},
            ])}
        horse = {"horseNumber": 7, "name": "コーゲンタフボーイ",
                 "recentRaces": [{"date": "2026-10-26", "track": "大井",
                                  "finish": 6, "fieldSize": 10,
                                  "timeSeconds": 91.6, "marginText": "2.5"}]}
        detail = target_detail([horse])
        stats = complete_detail_margins(
            detail, lambda rid: deepcopy(store.get(rid)), self.fetch_day_ids)
        self.assertEqual(stats["completed"], 0)
        self.assertNotIn("marginSeconds", detail["horses"][0]["recentRaces"][0])

    def test_existing_margin_and_jra_are_untouched(self):
        horse = {"horseNumber": 7, "name": "コーゲンタフボーイ",
                 "recentRaces": [{"date": "2026-10-26", "track": "大井",
                                  "finish": 6, "fieldSize": 10,
                                  "timeSeconds": 91.6, "marginSeconds": 9.9,
                                  "marginEvidenceSource": "nar_official_csv"}]}
        detail = target_detail([horse])
        stats = complete_detail_margins(detail, self.fetch_race, self.fetch_day_ids)
        run = detail["horses"][0]["recentRaces"][0]
        self.assertEqual(stats["completed"], 0)
        self.assertEqual(run["marginSeconds"], 9.9)
        self.assertEqual(run["marginEvidenceSource"], "nar_official_csv")

        jra = {"id": "jra-2026-11-15-東京-01", "date": "2026-11-15",
               "track": "東京", "circuit": "中央", "distance": 1600,
               "surface": "芝", "horses": [deepcopy(horse)]}
        jra["horses"][0]["recentRaces"] = [
            {"date": "2026-10-26", "track": "大井", "finish": 6,
             "fieldSize": 10, "timeSeconds": 91.6, "marginText": "2.5"}]
        stats = complete_detail_margins(jra, self.fetch_race, self.fetch_day_ids)
        self.assertEqual(stats["completed"], 0)
        self.assertNotIn("marginSeconds", jra["horses"][0]["recentRaces"][0])

    def test_completed_margin_makes_factor_available(self):
        horse = {"horseNumber": 7, "name": "コーゲンタフボーイ",
                 "recentRaces": [{"date": "2026-10-26", "track": "大井",
                                  "finish": 6, "fieldSize": 10,
                                  "timeSeconds": 91.6, "marginText": "2.5",
                                  "cornerPositions": [3, 3, 3]}]}
        detail = target_detail([horse])
        attach_model_evidence(detail)
        before = (detail["horses"][0].get("integratedEvaluation") or {}).get("narModelEvidence") or {}
        self.assertIsNone(before.get("margin"))
        complete_detail_margins(detail, self.fetch_race, self.fetch_day_ids)
        detail["horses"][0].pop("integratedEvaluation", None)
        attach_model_evidence(detail)
        after = (detail["horses"][0].get("integratedEvaluation") or {}).get("narModelEvidence") or {}
        self.assertIsNotNone(after.get("margin"))


def _analyzed_detail(version: str) -> dict:
    from arvexq.pipeline.fingerprints import analysis_input_hash
    horses = [
        {"horseNumber": n, "name": f"馬{n}", "jockey": "騎手",
         "carriedWeight": 57.0, "recentRaces": [], "allPastRuns": []}
        for n in (1, 2, 3)
    ]
    detail = {
        "id": "nar-2026-11-19-園田-01", "date": "2026-11-19",
        "track": "園田", "fieldSize": 3, "horses": horses,
        "preparedMeta": {"diagnosisReady": True},
        "researchEvidenceVersion": version,
        "researchEvidenceHorses": 3,
    }
    # attach_evidence always writes the per-horse blocks together with
    # the stamps; a genuinely analyzed detail carries both (the
    # _analysis_current gate counts the blocks, not just the stamps).
    for h in horses:
        h["researchEvidence"] = {
            "factors": {"version": "arvexq-empirical-fusion-v1",
                        "items": [{"key": "mineta", "weight": .60,
                                   "value": 0.5, "available": True},
                                  {"key": "margin", "weight": .40,
                                   "value": 0.5, "available": True}],
                        "calibrated": False},
            "sectionals": {}, "status": "nar-observed-only"}
    detail["preparedMeta"]["analysisInputHash"] = analysis_input_hash(detail)
    return detail


class EvidenceVersionGateTests(TestCase):
    def test_attach_evidence_stamps_current_version(self):
        detail = target_detail([{"horseNumber": 1, "name": "テスト",
                                 "recentRaces": []}])
        attach_evidence(detail)
        self.assertEqual(detail["researchEvidenceVersion"],
                         RESEARCH_EVIDENCE_VERSION)
        self.assertEqual(RESEARCH_EVIDENCE_VERSION, "arvexq-race-intelligence-v2")

    def test_v1_stamped_detail_is_not_analysis_current(self):
        # Fully analyzed and hash-current, but decorated by the previous
        # evidence logic: re-analyze once so margin completion reaches it.
        detail = _analyzed_detail("arvexq-race-intelligence-v1")
        self.assertFalse(prefetch._analysis_current(detail))

    def test_current_version_stamped_detail_is_analysis_current(self):
        detail = _analyzed_detail(RESEARCH_EVIDENCE_VERSION)
        self.assertTrue(prefetch._analysis_current(detail))
