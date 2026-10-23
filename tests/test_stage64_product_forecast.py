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
        assert [x["kind"] for x in items] == ["馬連", "ワイド", "馬単", "3連複"]
        assert all(0 < len(x["combos"]) <= 5 for x in items)
        assert len(prediction["stages"]) == 6
        assert len(prediction["stages"]["pace"]["value"]) == (1 if circuit == "中央" else 4)


def test_public_projection_contains_prediction_marks_and_bets_without_mutating_input():
    detail = race("地方")
    original = deepcopy(detail)
    published = with_preoff_clock(public_race, detail)
    assert published["predictionStatus"] == "ready"
    assert published["predictionMarks"]
    assert {x["mark"] for x in published["predictionMarks"]} == {"◎", "○", "▲", "△", "☆"}
    assert {x["kind"] for x in published["recommendedBets"]} == {"馬連", "ワイド", "馬単", "3連複"}
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


def test_d1_prefetch_product_attachment_preserves_original_evidence():
    from scripts.arvexq_prefetch import _attach_existing_stage64_products
    from scripts.arvexq_select_prefetch_repairs import repair_reason

    original = race("地方")
    original["predictionStatus"] = "disabled"
    original["predictionModelVersion"] = "arvexq-prediction-removed"
    original["preRacePrediction"] = {"frozen": True, "horses": [{"horseNumber": 1, "mark": "◎"}]}
    original["arvexqFullPayload"] = {"version": "retained-test-envelope"}
    snapshot = deepcopy(original)
    enriched = with_preoff_clock(_attach_existing_stage64_products, original)
    assert original == snapshot
    assert enriched["preRacePrediction"] == snapshot["preRacePrediction"]
    assert enriched["arvexqFullPayload"] == snapshot["arvexqFullPayload"]
    assert enriched["predictionStatus"] == "ready"
    assert enriched["predictionModelVersion"] == "arvexq-stage64-product-v1"
    assert len(enriched["predictionMarks"]) == 5
    assert len(enriched["recommendedBets"]) == 4
    assert repair_reason(enriched, original) == "stage64_products_not_persisted"


def test_d1_product_projection_never_retroactively_creates_off_predictions():
    from scripts.arvexq_prefetch import _attach_existing_stage64_products

    finished = race("中央")
    finished["result"] = {"status": "確定", "finishers": [{"horseNumber": 1, "finish": 1}]}
    finished["preRacePrediction"] = {"frozen": True}
    snapshot = deepcopy(finished)
    projected = with_preoff_clock(_attach_existing_stage64_products, finished)
    assert projected == snapshot
    assert finished == snapshot
    assert "predictionMarks" not in projected
    assert "recommendedBets" not in projected


def test_research_overlay_never_replaces_approved_preoff_stage64_products():
    from scripts.arvexq_apply_learned_overlay import apply

    original = with_preoff_clock(public_race, race("地方"))
    assert original["predictionStatus"] == "ready"
    assert original["predictionModelVersion"] == "arvexq-stage64-product-v1"
    assert len(original["predictionMarks"]) == 5
    assert original["recommendedBets"]
    sealed = {"frozen": True, "originalReference": "immutable-evidence"}
    original["preRacePrediction"] = sealed
    bundle = {"details": [deepcopy(original)], "summaries": []}
    result, report = apply(bundle, {"地方": {"training": {"lastDate": "2026-10-22"}}})
    assert result["details"][0] == original
    assert bundle["details"][0] == original
    assert report["skipped"][original["id"]] == "approved-stage64-product-preserved"
    assert result["details"][0]["preRacePrediction"] == sealed


def test_unapproved_research_overlay_still_cannot_fabricate_stage64_products():
    from scripts.arvexq_apply_learned_overlay import apply

    unready = race("地方")
    unready["predictionStatus"] = "disabled"
    unready["predictionModelVersion"] = "arvexq-prediction-removed"
    result, report = apply({"details": [unready]}, {})
    assert result["details"][0]["predictionStatus"] == "new-model-unavailable"
    assert "predictionMarks" not in result["details"][0]
    assert "recommendedBets" not in result["details"][0]


def test_nar_all_past_runs_alias_recovers_preoff_marks_without_changing_evidence():
    detail = race("地方")
    for horse in detail["horses"]:
        horse["allPastRuns"] = horse.pop("recentRaces")
    original = deepcopy(detail)
    published = with_preoff_clock(public_race, detail)
    assert published["predictionStatus"] == "ready"
    assert {m["mark"] for m in published["predictionMarks"]} == {"◎", "○", "▲", "△", "☆"}
    assert detail == original


def test_nar_alias_never_overrides_existing_recent_history_or_missing_evidence():
    detail = race("地方")
    detail["horses"][0]["recentRaces"] = []
    detail["horses"][0]["allPastRuns"] = [{"date": "2026-10-15", "fieldSize": 5, "finish": 1}]
    # Existing missing-corner guard remains enforced, even with an alias.
    assert build_prediction(detail, now=NOW) is None
    detail["horses"][0]["allPastRuns"] = []
    assert build_prediction(detail, now=NOW) is None


def test_nar_history_alias_does_not_change_central_or_started_races():
    jra = race("中央")
    for horse in jra["horses"]:
        horse["allPastRuns"] = horse.pop("recentRaces")
    assert build_prediction(jra, now=NOW) is None
    nar = race("地方")
    for horse in nar["horses"]:
        horse["allPastRuns"] = horse.pop("recentRaces")
    assert build_prediction(nar, now=datetime(2026, 10, 23, 13, 0, tzinfo=ZoneInfo("Asia/Tokyo"))) is None
