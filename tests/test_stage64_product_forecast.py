from copy import deepcopy
from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from arvexq.forecast.engine import build_prediction
from arvexq.forecast.marks import generate_marks
from arvexq.forecast.publication import public_race
from arvexq.forecast.tickets import generate_tickets
from app import _compact_display_snapshot


def race(circuit):
    prefix = "jra" if circuit == "中央" else "nar"
    return {
        "id": f"{prefix}-2026-10-23-試験場-01", "date": "2026-10-23",
        "circuit": circuit, "track": "東京" if circuit == "中央" else "大井",
        "surface": "芝" if circuit == "中央" else "ダート", "analysisMode": "平地",
        "startTime": "12:00", "fieldSize": 5,
        "horses": [{"horseNumber": n, "recentRaces": [
            {"date": "2026-10-15", "finish": n, "fieldSize": 5,
             "passing": [n], "track": "試験場"}
        ]} for n in range(1, 6)],
    }


NOW = datetime(2026, 10, 23, 10, 0, tzinfo=ZoneInfo("Asia/Tokyo"))


def with_preoff_clock(fn, detail):
    """Keep the October 23 start-date contract independent of CI wall-clock."""
    with patch("arvexq.forecast.engine.datetime") as clock:
        clock.now.return_value = NOW
        clock.fromisoformat.side_effect = datetime.fromisoformat
        return fn(detail)


def test_jra_and_nar_are_separate_and_publish_all_six_products():
    for circuit in ("中央", "地方"):
        prediction = build_prediction(race(circuit), now=NOW)
        assert prediction["predictionStatus"] == "ready"
        assert prediction["stage64ModelVersion"] in {"jra-flat-shadow-v1", "nar-flat-shadow-v1"}
        assert len(generate_marks(prediction)) == 5
        assert {x["mark"] for x in generate_marks(prediction)} == {"◎", "○", "▲", "△", "☆"}
        items = generate_tickets(prediction, generate_marks(prediction))
        assert sum(x["points"] for x in items) == 5
        assert sum(len(x["combos"]) for x in items) == 5
        assert all(x["points"] == len(x["combos"]) for x in items)
        assert len(prediction["stages"]) == 6
        assert len(prediction["stages"]["pace"]["value"]) == (1 if circuit == "中央" else 2)


def test_public_projection_contains_prediction_marks_and_bets_without_mutating_input():
    detail = race("地方")
    original = deepcopy(detail)
    published = with_preoff_clock(public_race, detail)
    assert published["predictionStatus"] == "ready"
    assert published["predictionMarks"]
    assert {x["mark"] for x in published["predictionMarks"]} == {"◎", "○", "▲", "△", "☆"}
    assert sum(x["points"] for x in published["recommendedBets"]) == 5
    assert detail == original


def test_started_or_result_race_never_gets_a_forecast():
    detail = race("中央")
    assert build_prediction(detail, now=datetime(2026, 10, 23, 13, 0, tzinfo=ZoneInfo("Asia/Tokyo"))) is None
    detail["result"] = {"finishers": [{"horseNumber": 1, "finish": 1}]}
    assert public_race(detail)["predictionStatus"] == "disabled"


def test_api_compact_projection_keeps_ready_products_for_the_detail_ui():
    compact = with_preoff_clock(_compact_display_snapshot, race("中央"))
    assert compact["predictionStatus"] == "ready"
    assert compact["predictionModelVersion"] == "arvexq-stage64-product-v1"
    assert compact["predictionMarks"]
    assert compact["recommendedBets"]


def test_stage64_wager_marginals_are_from_existing_three_place_joint():
    from arvexq.forecast.tickets import _score

    probs = {"win": {1: 0.4, 2: 0.4, 3: 0.1, 4: 0.1}, "trifecta": [
        {"combo": [1, 2, 3], "probability": 0.4},
        {"combo": [2, 1, 4], "probability": 0.1},
        {"combo": [2, 3, 4], "probability": 0.3},
        {"combo": [4, 3, 1], "probability": 0.2},
    ]}
    assert abs(_score(probs, (1, 2), "馬連") - 0.5) < 1e-12
    assert abs(_score(probs, (1, 2), "馬単") - 0.4) < 1e-12
    assert abs(_score(probs, (2, 3), "ワイド") - 0.7) < 1e-12
    assert abs(_score(probs, (1, 2, 3), "3連複") - 0.4) < 1e-12
    assert abs(_score(probs, (3, 4), "馬連") - 0.2) < 1e-12
    assert _score(probs, (1, 4), "馬連") == 0.0


def test_pending_placeholder_is_not_confused_with_a_confirmed_result():
    detail = race("地方")
    detail["result"] = {"status": "未確定", "finishers": [], "payouts": []}
    assert build_prediction(detail, now=NOW)["predictionStatus"] == "ready"
    detail["result"]["finishers"] = [{"horseNumber": 1, "finish": 1}]
    assert build_prediction(detail, now=NOW) is None
    detail["result"] = {"status": "未確定", "finishers": [], "payouts": [{"type": "単勝"}]}
    assert build_prediction(detail, now=NOW) is None
    detail["result"] = {"status": "確定", "finishers": [], "payouts": []}
    assert build_prediction(detail, now=NOW) is None


def test_recommended_tickets_rank_across_wager_types_not_five_per_kind():
    prediction = {"predictionStatus": "ready", "stages": {"probability": {"value": {
        "trifecta": [
            {"combo": [1, 2, 3], "probability": 0.55},
            {"combo": [2, 1, 3], "probability": 0.25},
            {"combo": [3, 2, 1], "probability": 0.20},
        ],
    }}}}
    marks = [{"horseNumber": n, "mark": mark} for n, mark in
             [(1, "◎"), (2, "○"), (3, "▲")]]
    bets = generate_tickets(prediction, marks)
    assert sum(bet["points"] for bet in bets) == 5
    all_candidates = []
    from itertools import combinations, permutations
    from arvexq.forecast.tickets import _score
    for kind, size in (("馬連", 2), ("ワイド", 2), ("馬単", 2), ("3連複", 3)):
        for combo in (permutations([1, 2, 3], size) if kind == "馬単"
                      else combinations([1, 2, 3], size)):
            score = _score(prediction["stages"]["probability"]["value"], combo, kind)
            if score > 0:
                all_candidates.append((-score, kind, combo))
    expected = sorted(all_candidates)[:5]
    actual = [(kind, tuple(combo)) for bet in bets for kind in [bet["kind"]]
              for combo in bet["combos"]]
    assert sorted(actual) == sorted((kind, combo) for _, kind, combo in expected)


def test_race_reading_uses_runner_relations_without_fake_expert_votes():
    detail = race("地方")
    prediction = build_prediction(detail, now=NOW)
    reading = prediction["raceReading"]
    assert reading["expertFusionStatus"] == "methodology-only-no-expert-picks"
    assert reading["raceSituation"] == "単騎逃げ・先行負荷軽め"
    assert len(prediction["stages"]["pace"]["value"]) == 2
    assert reading["horses"][1]["predictedPosition"] == "逃げ"
    assert reading["horses"][1]["winningScenario"] == "先手を確保して粘り込む展開"
    assert prediction["stages"]["marks"]["reasoning"][1]["winScenario"]
    assert prediction["stages"]["tickets"]["constructionRule"]


def test_race_reading_does_not_cross_jra_nar_baselines():
    central = build_prediction(race("中央"), now=NOW)
    local = build_prediction(race("地方"), now=NOW)
    assert len(central["stages"]["pace"]["value"]) == 1
    assert len(local["stages"]["pace"]["value"]) == 2
    assert central["raceReading"]["raceSituation"] != local["raceReading"]["raceSituation"]


def test_handicapping_methods_have_observed_evidence_and_no_fabricated_votes():
    prediction = build_prediction(race("地方"), now=NOW)
    for horse in prediction["raceReading"]["horses"].values():
        lenses = horse["methodologyFusion"]
        assert set(lenses) == {"回顧型", "能力比較型", "コース適性型", "展開型"}
        assert all(isinstance(lens["evidenceRuns"], int) for lens in lenses.values())
        assert "expertVotes" not in horse
        assert horse["unverified"]


def test_supplemental_race_analysis_uses_only_existing_evidence():
    detail = race("地方")
    detail["horses"][0]["jockey"] = "騎手C"
    detail["horses"][0]["recentRaces"] = [
        {"date": "2026-10-15", "finish": 1, "fieldSize": 5,
         "passing": [1], "track": "大井", "first3F": 36.4, "jockey": "騎手A"},
        {"date": "2026-10-01", "finish": 2, "fieldSize": 5,
         "passing": [2], "track": "大井", "first3F": 37.1, "jockey": "騎手B"},
    ]
    prediction = build_prediction(detail, now=NOW)
    observed = prediction["raceReading"]["horses"][1]["supplementalEvidence"]
    unknown = prediction["raceReading"]["horses"][2]["supplementalEvidence"]
    assert observed["pastPaceEvidence"]["observedFirst3F"] == [36.4, 37.1]
    assert observed["trackComparison"]["sameTrackRuns"] == 2
    assert observed["jockeyChangeEvidence"]["status"] == "changed"
    assert unknown["jockeyChangeEvidence"]["status"] == "unknown"
    assert unknown["pastPaceEvidence"]["status"] == "missing"
    assert unknown["trackBias"]["status"] == "unverified"
    assert unknown["oddsTimeline"]["status"] == "unverified"
    assert prediction["raceReading"]["expertFusionStatus"] == "methodology-only-no-expert-picks"


def test_existing_marks_expose_race_reading_and_course_evidence():
    detail = race("地方")
    detail["horses"][0]["recentRaces"][0]["track"] = "大井"
    prediction = build_prediction(detail, now=NOW)
    first = next(row for row in generate_marks(prediction) if row["horseNumber"] == 1)
    assert first["raceReason"] == "先手を確保して粘り込む展開"
    assert first["predictedPosition"] == "逃げ"
    assert first["observedEvidence"]["trackComparison"]["sameTrackRuns"] == 1
    assert prediction["stages"]["marks"]["reasoning"][1]["supplementalEvidence"]


def test_marks_prioritize_viable_win_paths_across_pace_scenarios():
    from arvexq.research.stage64.marks import roles
    win = {1: 0.46, 2: 0.39, 3: 0.15}
    top3 = {1: 0.8, 2: 0.7, 3: 0.5}
    scenario_wins = [{1: 0.8, 2: 0.15, 3: 0.05},
                     {1: 0.12, 2: 0.63, 3: 0.25}]
    result = roles(win, top3, scenario_wins)
    assert result["decisionMethod"] == "scenario-robust-win"
    assert result["orderedWinCandidates"][0] == 2
    assert roles(win, top3, [scenario_wins[0]])["orderedWinCandidates"][0] == 1


def test_stage64_marks_follow_selected_pace_scenarios():
    local = build_prediction(race("地方"), now=NOW)
    central = build_prediction(race("中央"), now=NOW)
    assert local["stages"]["marks"]["value"]["decisionMethod"] == "scenario-robust-win"
    assert central["stages"]["marks"]["value"]["decisionMethod"] == "aggregate-win"
    assert generate_marks(local)[0]["horseNumber"] == local["stages"]["marks"]["value"]["orderedWinCandidates"][0]


def test_unsaved_external_race_input_is_accepted_without_motherduck():
    """Research calculation must not require a stored snapshot or DB record."""
    from arvexq.research.stage64.pipeline import predict
    from arvexq.research.stage63.probability import distribution
    from arvexq.research.stage64.marks import roles
    for day in ("2026-09-15", "2026-09-22", "2026-10-02"):
        detail = race("地方")
        detail["id"] = f"nar-{day}-架空場-01"
        detail["date"] = day
        for horse in detail["horses"]:
            horse["recentRaces"][0]["date"] = "2026-08-10"
        # In-memory pre-race inputs: no database connection, no future outcomes.
        result = predict(detail, expected_circuit="nar")
        assert not result["blockers"]
        assert len(result["stages"]) == 6
        assert result["stages"]["marks"]["value"]["orderedWinCandidates"]
        assert result["raceReading"]["horses"]
