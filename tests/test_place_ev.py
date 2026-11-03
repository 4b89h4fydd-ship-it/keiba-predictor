"""Place （複勝） EV + combined gate + 注 overlay (2026-11-04).

The feature: per-runner place EV ranges (payout probability from
the same Plackett-Luce marginals as the win EV x the OBSERVED
place odds range), the combined gate (win EV >= 1.25 AND win
probability >= 0.05 AND place EV lower bound >= 1.0), and the 注
attention overlay for qualifiers. Plus the one-time
"place-ev-upgrade" re-issue that adds the place side to v9b
forecasts frozen before the upstream sync carried place odds —
surgically, with the stored probabilities/marks/tickets untouched.

Honesty pins throughout: no place range is ever derived from win
odds, a missing range stays missing, and the upgrade fails closed.
"""
from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch
from zoneinfo import ZoneInfo

from rewrite.analysis.forecast import RaceForecast, RunnerForecast
from rewrite.analysis.tickets import generate_tickets
from rewrite.data.normalize import normalize_runner
from rewrite.output.api_shape import (
    MODEL_VERSION, _marks, _ticket_plan_block, combined_gate_picks)
from rewrite.safety.probability import distribution, marginals

JST = ZoneInfo("Asia/Tokyo")


# ------------------------------------------------------------ sync side


class OddsLatestPlaceProjectionTests(TestCase):
    def test_place_range_recovered_from_raw_json(self):
        import app
        with tempfile.TemporaryDirectory() as td:
            bank = app.RaceDataBank(Path(td) / "racedb.sqlite3")
            bank.save_odds("nar-2026-11-04-園田-01", [
                {"horseNumber": 3, "winOdds": 11.1, "popularity": 5,
                 "oddsSource": "netkeiba実オッズ",
                 "placeOddsLow": 2.6, "placeOddsHigh": 3.4},
                {"horseNumber": 4, "winOdds": 135.1, "popularity": 12,
                 "oddsSource": "netkeiba実オッズ"},
            ], "netkeiba実オッズ")
            rows = {r["horseNumber"]: r for r in bank.odds_latest(
                "nar-2026-11-04-園田-01")}
        self.assertEqual(rows[3]["placeOddsLow"], 2.6)
        self.assertEqual(rows[3]["placeOddsHigh"], 3.4)
        self.assertEqual(rows[3]["winOdds"], 11.1)
        # Absent stays absent: no key, never an imputed value.
        self.assertNotIn("placeOddsLow", rows[4])
        self.assertNotIn("placeOddsHigh", rows[4])


class NetkeibaJraPlaceParserTests(TestCase):
    def test_list_range_entries(self):
        from arvexq.ingest.netkeiba_odds_parser import (
            _parse_netkeiba_place_odds_payload)
        raw = ('{"data":{"odds":{"1":{"3":["11.1","0","5"]},'
               '"2":{"3":["2.6","3.4","5"],"4":["18.0","30.5","12"]}}}}')
        out = _parse_netkeiba_place_odds_payload(raw)
        self.assertEqual(out[3], {"placeOddsLow": 2.6,
                                  "placeOddsHigh": 3.4})
        self.assertEqual(out[4], {"placeOddsLow": 18.0,
                                  "placeOddsHigh": 30.5})

    def test_single_value_means_low_equals_high(self):
        from arvexq.ingest.netkeiba_odds_parser import (
            _parse_netkeiba_place_odds_payload)
        out = _parse_netkeiba_place_odds_payload(
            '{"data":{"odds":{"2":{"1":["1.1"]}}}}')
        self.assertEqual(out[1], {"placeOddsLow": 1.1,
                                  "placeOddsHigh": 1.1})

    def test_garbage_yields_nothing(self):
        from arvexq.ingest.netkeiba_odds_parser import (
            _parse_netkeiba_place_odds_payload)
        for raw in ("", "not json", '{"data":{"odds":{"1":{}}}}',
                    '{"data":{"odds":{"2":{"1":["-","-","1"]}}}}',
                    '{"data":{"odds":{"2":{"1":["3.0","2.0","1"]}}}}'):
            self.assertEqual(_parse_netkeiba_place_odds_payload(raw), {},
                             raw)


class NarNetkeibaB1PlaceTests(TestCase):
    SHUTUBA = """<html><body><table>
    <tr class="HorseList"><td class="Umaban">1</td><td>アアア</td></tr>
    <tr class="HorseList"><td class="Umaban">2</td><td>イイイ</td></tr>
    </table></body></html>"""
    B1 = """<html><body><table>
    <tr><th>馬番</th><th>馬名</th><th>単勝オッズ</th><th>複勝オッズ</th><th>人気</th></tr>
    <tr><td>1</td><td>アアア</td><td>2.4</td><td>1.1 - 1.3</td><td>1</td></tr>
    <tr><td>2</td><td>イイイ</td><td>11.1</td><td>2.6 - 3.4</td><td>5</td></tr>
    </table></body></html>"""

    def test_b1_place_column_is_parsed(self):
        import app
        detail = {"date": "2026-11-04", "track": "園田", "raceNumber": 1}
        with patch.object(app, "_netkeiba_get",
                          side_effect=[self.SHUTUBA, self.B1]):
            rows = app._nar_netkeiba_preview_rows(detail)
        self.assertEqual(rows[1]["winOdds"], 2.4)
        self.assertEqual(rows[1]["placeOddsLow"], 1.1)
        self.assertEqual(rows[1]["placeOddsHigh"], 1.3)
        self.assertEqual(rows[2]["winOdds"], 11.1)
        self.assertEqual(rows[2]["placeOddsLow"], 2.6)
        self.assertEqual(rows[2]["placeOddsHigh"], 3.4)


# ------------------------------------------------------- normalize side


class NormalizePlaceOddsTests(TestCase):
    def test_runner_carries_place_range(self):
        row = {"horseNumber": 3, "name": "アセンディア",
               "winOdds": 11.1, "placeOddsLow": 2.6, "placeOddsHigh": 3.4,
               "recentRaces": []}
        runner = normalize_runner(row, "2026-11-04", "test")
        self.assertTrue(runner.place_odds_low.present)
        self.assertEqual(runner.place_odds_low.value, 2.6)
        self.assertEqual(runner.place_odds_high.value, 3.4)

    def test_missing_place_range_stays_missing(self):
        row = {"horseNumber": 3, "name": "アセンディア",
               "winOdds": 11.1, "recentRaces": []}
        runner = normalize_runner(row, "2026-11-04", "test")
        self.assertFalse(runner.place_odds_low.present)
        self.assertFalse(runner.place_odds_high.present)


# --------------------------------------------------------- tickets side


def _forecast(strengths: dict) -> RaceForecast:
    probs = marginals(distribution(strengths))
    runners = [RunnerForecast(
        number=n, name=f"馬{n}", ability_score=0.5, strength=s,
        pace_adjustment=1.0, pace_reasons=(), p_win=probs[n][0],
        p_top2=probs[n][1], p_top3=probs[n][2], mark="", status="scored")
        for n, s in sorted(strengths.items())]
    return RaceForecast("nar-test-01", 3.0, "uncalibrated-prior",
                        tuple(runners), "ok")


class PlaceEstimateTests(TestCase):
    STRENGTHS = {n: 1.1 - 0.08 * n for n in range(1, 11)}

    def test_estimates_use_top3_marginals_and_range(self):
        forecast = _forecast(self.STRENGTHS)
        plan = generate_tickets(
            forecast, {n: 5.0 for n in self.STRENGTHS},
            calibration_validated=False,
            place_odds={3: (2.6, 3.4), 5: (1.4, 1.9)})
        by_no = {e.number: e for e in plan.place_ev_estimates}
        self.assertEqual(sorted(by_no), [3, 5])
        expected_p = marginals(distribution(
            {r.number: r.strength for r in forecast.runners}))[3][2]
        self.assertEqual(by_no[3].probability, round(expected_p, 4))
        self.assertEqual(by_no[3].expected_value_low,
                         round(expected_p * 2.6, 4))
        self.assertEqual(by_no[3].expected_value_high,
                         round(expected_p * 3.4, 4))
        # Sorted by lower bound descending; ev_place suppression lifted.
        lows = [e.expected_value_low for e in plan.place_ev_estimates]
        self.assertEqual(lows, sorted(lows, reverse=True))
        self.assertNotIn("ev_place", plan.suppressed)

    def test_small_field_uses_top2_probability(self):
        strengths = {n: 1.0 - 0.1 * n for n in range(1, 7)}
        forecast = _forecast(strengths)
        plan = generate_tickets(
            forecast, {n: 4.0 for n in strengths},
            calibration_validated=False, place_odds={2: (1.5, 2.0)})
        expected_p = marginals(distribution(strengths))[2][1]
        self.assertEqual(plan.place_ev_estimates[0].probability,
                         round(expected_p, 4))

    def test_no_place_market_at_four_or_fewer(self):
        strengths = {n: 1.0 - 0.1 * n for n in range(1, 5)}
        plan = generate_tickets(
            _forecast(strengths), {n: 4.0 for n in strengths},
            calibration_validated=False, place_odds={1: (1.2, 1.5)})
        self.assertEqual(plan.place_ev_estimates, ())

    def test_no_place_odds_no_estimates_and_suppression_kept(self):
        plan = generate_tickets(
            _forecast(self.STRENGTHS), {n: 5.0 for n in self.STRENGTHS},
            calibration_validated=False)
        self.assertEqual(plan.place_ev_estimates, ())
        self.assertEqual(plan.suppressed.get("ev_place"),
                         "odds-unavailable")

    def test_invalid_ranges_are_skipped(self):
        plan = generate_tickets(
            _forecast(self.STRENGTHS), {n: 5.0 for n in self.STRENGTHS},
            calibration_validated=False,
            place_odds={3: (3.4, 2.6), 4: (0.5, 1.2), 5: (1.3, 1.8)})
        self.assertEqual([e.number for e in plan.place_ev_estimates], [5])


class CombinedGateTests(TestCase):
    def _plan(self):
        strengths = {n: 1.1 - 0.08 * n for n in range(1, 11)}
        forecast = _forecast(strengths)
        # Win odds chosen so: #1 EV high & p high, #2 EV high but
        # p < 5% is impossible with these strengths; instead drive
        # the gate through place ranges: #1 place low small.
        win_odds = {n: 30.0 for n in strengths}
        place_odds = {1: (1.1, 1.2), 2: (4.0, 5.0), 3: (1.05, 1.1)}
        return generate_tickets(forecast, win_odds,
                                calibration_validated=False,
                                place_odds=place_odds)

    def test_gate_requires_all_three_conditions(self):
        plan = self._plan()
        picks = combined_gate_picks(plan)
        win = {t.selection[0]: t for t in plan.win_ev_estimates}
        place = {e.number: e for e in plan.place_ev_estimates}
        for n in picks:
            self.assertGreaterEqual(win[n].expected_return, 1.25)
            self.assertGreaterEqual(win[n].probability, 0.05)
            self.assertGreaterEqual(place[n].expected_value_low, 1.0)
        # #1: win side passes but place lower bound < 1.0 -> excluded.
        self.assertNotIn(1, picks)
        self.assertLess(place[1].expected_value_low, 1.0)
        # #2 passes everything.
        self.assertIn(2, picks)

    def test_ticket_plan_block_shape(self):
        plan = self._plan()
        block = _ticket_plan_block(plan, calibrated=True)
        self.assertIn("placeExpectedValues", block)
        self.assertEqual(block["combinedPicks"], combined_gate_picks(plan))
        entry = block["placeExpectedValues"][0]
        self.assertEqual(
            sorted(entry),
            ["expectedValueHigh", "expectedValueLow", "horseNumber",
             "placeOddsHigh", "placeOddsLow", "top3Probability"])
        self.assertNotIn("ev_place", block["suppressed"])

    def test_block_without_place_material_has_no_keys(self):
        plan = generate_tickets(
            _forecast({n: 1.0 - 0.05 * n for n in range(1, 9)}),
            {n: 5.0 for n in range(1, 9)}, calibration_validated=False)
        block = _ticket_plan_block(plan)
        self.assertNotIn("placeExpectedValues", block)
        self.assertNotIn("combinedPicks", block)

    def test_marks_attention_overlay(self):
        strengths = {n: 1.1 - 0.08 * n for n in range(1, 11)}
        forecast = _forecast(strengths)
        # Give #2 the ◎ mark manually via a marked forecast copy.
        runners = []
        for r in forecast.runners:
            runners.append(RunnerForecast(
                number=r.number, name=r.name,
                ability_score=r.ability_score, strength=r.strength,
                pace_adjustment=1.0, pace_reasons=(), p_win=0.2,
                p_top2=0.4, p_top3=0.6,
                mark="◎" if r.number == 2 else "", status="scored"))
        marked = RaceForecast(forecast.race_id, 3.0,
                              "uncalibrated-prior", tuple(runners), "ok")
        prediction_marks, unified_marks, _ = _marks(
            marked, attention={2, 7})
        by_no = {m["horseNumber"]: m for m in prediction_marks}
        self.assertTrue(by_no[2]["attention"])
        self.assertEqual(by_no[2]["mark"], "◎")
        # Unmarked qualifier: overlay carrier with an empty mark.
        self.assertEqual(by_no[7]["mark"], "")
        self.assertTrue(by_no[7]["attention"])
        unified_by_no = {m["horseNumber"]: m for m in unified_marks}
        self.assertTrue(unified_by_no[2]["attention"])
        self.assertNotIn(7, unified_by_no)


# --------------------------------------------------------- publish side

from arvexq.prediction.unified_product import (  # noqa: E402
    canonical_receipt, verified as verified_unified)
from scripts.arvexq_rewrite_publish import (  # noqa: E402
    V9B_LANE, _place_ev_upgrade_info, build_publish_detail)

RACE_ID = "nar-2026-11-04-園田-01"
DATE = "2026-11-04"
POST = "10:40"
PUBLISHED_AT = "2026-11-03T21:05:00+09:00"
NOW = datetime(2026, 11, 4, 2, 30, tzinfo=JST)  # >8h before post
NUMBERS = tuple(range(1, 11))
NAMES = {n: f"馬{n}" for n in NUMBERS}
WIN_ODDS = {1: 2.9, 2: 4.0, 3: 11.1, 4: 135.1, 5: 6.5,
            6: 142.1, 7: 12.5, 8: 4.1, 9: 40.2, 10: 9.2}
PLACE = {n: (1.5, 2.2) for n in NUMBERS}
PLACE[3] = (2.6, 3.4)   # gate passer (marked ▲)
PLACE[9] = (2.2, 3.0)   # gate passer (unmarked)
PLACE[5] = (1.2, 1.6)   # place lower bound too small
WIN_EV = {
    1: (0.2213, 2.9, 0.6418),
    2: (0.1440, 4.0, 0.5760),
    3: (0.1315, 11.1, 1.4597),   # win side passes
    4: (0.0137, 135.1, 1.8509),  # win probability < 5%
    5: (0.1200, 6.5, 1.3000),    # win side passes, place side fails
    7: (0.0920, 12.5, 1.1500),   # win EV < 1.25
    9: (0.1000, 40.2, 1.5000),   # both sides pass
    10: (0.1040, 9.2, 0.9568),
}
TOP3 = {1: 0.5833, 2: 0.4500, 3: 0.3986, 4: 0.0900, 5: 0.5500,
        6: 0.0600, 7: 0.3500, 8: 0.4300, 9: 0.5000, 10: 0.3900}
MARKS = {1: "◎", 2: "▲", 3: "△", 8: "○", 10: "☆"}


def stored_detail(*, lane=V9B_LANE, place=PLACE, revision=None,
                  with_place_block=False, post=POST,
                  numbers=NUMBERS) -> dict:
    horses = []
    for n in numbers:
        horse = {"horseNumber": n, "name": NAMES[n],
                 "winOdds": WIN_ODDS[n]}
        if place is not None and n in place:
            horse["placeOddsLow"], horse["placeOddsHigh"] = place[n]
        horses.append(horse)
    win_ev = [
        {"horseNumber": n, "winProbability": p, "odds": o,
         "expectedValue": ev}
        for n, (p, o, ev) in sorted(WIN_EV.items()) if n in numbers]
    plan = {
        "status": "参考候補", "items": [], "reason": "test",
        "sameModelAndMarks": True, "maximumPoints": 5,
        "expectedValue": None,
        "expectedValueStatus": "calibrated-estimate",
        "winExpectedValues": win_ev,
        "suppressed": {"ev_place": "odds-unavailable",
                       "ev_trio": "odds-unavailable"},
    }
    if with_place_block:
        plan["placeExpectedValues"] = []
        plan["combinedPicks"] = []
    unified = {
        "version": "arvexq-unified-live-v1",
        "raceId": RACE_ID, "raceDate": DATE, "circuit": "地方",
        "modelFamily": "flat",
        "capturedAt": "2026-11-03T21:00:00+09:00",
        "trainedThrough": "2026-10-23",
        "modelVersion": MODEL_VERSION,
        "modelHash": "b" * 64,
        "roster": [{"horseNumber": n, "name": NAMES[n]} for n in numbers],
        "marks": [
            {"horseNumber": n, "markSymbol": MARKS[n],
             "winProbabilityRange": None, "top3ProbabilityRange": None,
             "winProbability": 0.2, "top3Probability": TOP3[n],
             "reason": "test"}
            for n in sorted(MARKS) if n in numbers],
        "diagnosis": [
            {"horseNumber": n, "abilityScore": 0.5,
             "winProbability": 0.1, "top3Probability": TOP3[n],
             "reason": "test"}
            for n in numbers],
        "ticketPlan": plan,
        "researchOnly": True,
        "probabilitiesCalibrated": False,
    }
    receipt = canonical_receipt(unified)
    unified["receiptSha256"] = receipt
    marker = {
        "modelVersion": MODEL_VERSION,
        "publishedAt": PUBLISHED_AT,
        "receiptSha256": receipt,
        "abilityLane": lane,
        "temperature": 0.6692,
        "blendApplied": True,
        "postProcessing": {"type": "temperature+market-blend",
                           "temperature": 0.6692, "blendWeight": 0.5,
                           "blendApplied": True},
    }
    if revision is not None:
        marker["revision"] = revision
    prediction_marks = [
        {"horseNumber": n, "mark": MARKS[n], "winProbability": 0.2}
        for n in sorted(MARKS) if n in numbers]
    return {
        "id": RACE_ID, "date": DATE, "circuit": "地方", "track": "園田",
        "raceNumber": 1, "title": "テスト", "surface": "ダート",
        "scheduledStartTime": post, "startTime": post,
        "predictionStatus": "ready",
        "predictionModelVersion": MODEL_VERSION,
        "preparedMeta": {"rewritePublish": marker},
        "unifiedForecast": unified,
        "prediction": {"predictionMarks": [dict(m) for m in prediction_marks]},
        "predictionMarks": prediction_marks,
        "horses": horses,
    }


def _summary() -> dict:
    return {"race_id": RACE_ID, "id": RACE_ID}


class PlaceEvUpgradeQualificationTests(TestCase):
    def test_qualifies_when_all_conditions_hold(self):
        info = _place_ev_upgrade_info(stored_detail(), NOW)
        self.assertIsNotNone(info)
        self.assertEqual(info["reason"], "place-ev-upgrade")
        self.assertEqual(len(info["placeOdds"]), 10)

    def test_already_carrying_place_block_is_final(self):
        detail = stored_detail(with_place_block=True)
        self.assertIsNone(_place_ev_upgrade_info(detail, NOW))

    def test_existing_upgrade_revision_blocks(self):
        revision = {"kind": "place-ev-upgrade",
                    "reason": "place-ev-upgrade",
                    "revisedAt": "2026-11-04T02:30:00+09:00",
                    "revisionCount": 1, "previousReceiptSha256": "c" * 64}
        self.assertIsNone(_place_ev_upgrade_info(
            stored_detail(revision=revision), NOW))

    def test_other_lanes_never_qualify(self):
        for lane in ("v8-elo-speed2", "v1-prior"):
            self.assertIsNone(
                _place_ev_upgrade_info(stored_detail(lane=lane), NOW),
                lane)

    def test_incomplete_place_coverage_never_qualifies(self):
        place = dict(PLACE)
        del place[10]
        self.assertIsNone(_place_ev_upgrade_info(
            stored_detail(place=place), NOW))

    def test_inverted_range_never_qualifies(self):
        place = dict(PLACE)
        place[4] = (3.0, 2.0)
        self.assertIsNone(_place_ev_upgrade_info(
            stored_detail(place=place), NOW))

    def test_small_field_never_qualifies(self):
        # Seven or fewer: the stored product has no top-2
        # probability to price the place side with.
        detail = stored_detail(numbers=tuple(range(1, 8)))
        self.assertIsNone(_place_ev_upgrade_info(detail, NOW))

    def test_post_guard(self):
        late = datetime(2026, 11, 4, 9, 41, tzinfo=JST)  # 59 min
        self.assertIsNone(_place_ev_upgrade_info(stored_detail(), late))
        edge = datetime(2026, 11, 4, 9, 40, tzinfo=JST)  # exactly 60
        self.assertIsNotNone(_place_ev_upgrade_info(stored_detail(), edge))


class PlaceEvUpgradeBuildTests(TestCase):
    def test_build_adds_place_side_and_keeps_stored_forecast(self):
        old = stored_detail()
        new, receipt = build_publish_detail(old, _summary(), NOW)
        self.assertIsNotNone(new, receipt)
        plan = new["unifiedForecast"]["ticketPlan"]
        entries = {e["horseNumber"]: e
                   for e in plan["placeExpectedValues"]}
        self.assertEqual(sorted(entries), list(NUMBERS))
        # Place side priced from the STORED top-3 probabilities.
        self.assertEqual(entries[3]["top3Probability"], TOP3[3])
        self.assertEqual(entries[3]["expectedValueLow"],
                         round(TOP3[3] * 2.6, 4))
        self.assertEqual(entries[3]["expectedValueHigh"],
                         round(TOP3[3] * 3.4, 4))
        # Entries sorted by lower bound descending.
        lows = [e["expectedValueLow"] for e in plan["placeExpectedValues"]]
        self.assertEqual(lows, sorted(lows, reverse=True))
        # Combined gate: #3 (marked) and #9 (unmarked) only.
        self.assertEqual(plan["combinedPicks"], [9, 3] if
                         entries[9]["expectedValueLow"] >=
                         entries[3]["expectedValueLow"] else [3, 9])
        self.assertEqual(sorted(plan["combinedPicks"]), [3, 9])
        self.assertNotIn("ev_place", plan["suppressed"])
        self.assertEqual(plan["suppressed"].get("ev_trio"),
                         "odds-unavailable")
        # Attention overlay: unified marks + predictionMarks.
        unified_marks = {m["horseNumber"]: m
                         for m in new["unifiedForecast"]["marks"]}
        self.assertTrue(unified_marks[3].get("attention"))
        self.assertNotIn(9, unified_marks)
        prediction_marks = {m["horseNumber"]: m
                            for m in new["predictionMarks"]}
        self.assertTrue(prediction_marks[3].get("attention"))
        self.assertEqual(prediction_marks[3]["mark"], "△")
        self.assertEqual(prediction_marks[9]["mark"], "")
        self.assertTrue(prediction_marks[9].get("attention"))
        self.assertEqual(
            {m["horseNumber"]: m for m in
             new["prediction"]["predictionMarks"]}[9]["attention"], True)
        # Stored forecast content is otherwise untouched.
        self.assertEqual(plan["winExpectedValues"],
                         old["unifiedForecast"]["ticketPlan"]
                         ["winExpectedValues"])
        self.assertEqual(
            {m["horseNumber"]: m["markSymbol"] for m in
             new["unifiedForecast"]["marks"]},
            {m["horseNumber"]: m["markSymbol"] for m in
             old["unifiedForecast"]["marks"]})
        # Revision stamped; lane and first publication preserved.
        marker = new["preparedMeta"]["rewritePublish"]
        self.assertEqual(marker["abilityLane"], V9B_LANE)
        self.assertTrue(marker["blendApplied"])
        self.assertEqual(marker["firstPublishedAt"], PUBLISHED_AT)
        revision = marker["revision"]
        self.assertEqual(revision["kind"], "place-ev-upgrade")
        self.assertEqual(revision["revisionCount"], 1)
        self.assertEqual(revision["previousReceiptSha256"],
                         old["unifiedForecast"]["receiptSha256"])
        self.assertEqual(marker["receiptSha256"], receipt)
        # The re-issued product self-verifies like a build product.
        check = verified_unified(
            dict(old, unifiedForecast=new["unifiedForecast"]))
        self.assertIsNotNone(check)

    def test_upgraded_race_never_requalifies(self):
        old = stored_detail()
        new, _receipt = build_publish_detail(old, _summary(), NOW)
        self.assertIsNotNone(new)
        self.assertIsNone(_place_ev_upgrade_info(new, NOW))
        again, reason = build_publish_detail(new, _summary(), NOW)
        self.assertIsNone(again)
        self.assertTrue(reason.startswith("frozen:"), reason)

    def test_unqualified_frozen_race_stays_frozen(self):
        place = dict(PLACE)
        del place[10]
        new, reason = build_publish_detail(
            stored_detail(place=place), _summary(), NOW)
        self.assertIsNone(new)
        self.assertTrue(reason.startswith("frozen:"), reason)
