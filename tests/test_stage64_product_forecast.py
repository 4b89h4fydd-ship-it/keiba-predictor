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
        assert prediction["stage64ModelVersion"] == (
            "jra-flat-shadow-v1" if circuit == "中央"
            else "nar-flat-shadow-v2-observed-career"
        )
        assert len(generate_marks(prediction)) == 5
        assert {x["mark"] for x in generate_marks(prediction)} == {"◎", "○", "▲", "△", "☆"}
        items = generate_tickets(prediction, generate_marks(prediction))
        assert 1 <= sum(x["points"] for x in items) <= 5
        assert 1 <= sum(len(x["combos"]) for x in items) <= 5
        assert len(prediction["stages"]) == 6
        assert len(prediction["stages"]["pace"]["value"]) == 1
        assert prediction["paceEvidence"]["actualPaceVerified"] is False
        assert "単騎逃げ・ハイペース・差し有利とは断定せず" in prediction["forecastText"]
        if circuit == "中央":
            assert "中央競馬方式：" in prediction["forecastText"]
            assert "地方競馬方式：" not in prediction["forecastText"]
        else:
            assert "地方競馬方式：" in prediction["forecastText"]
            assert "中央競馬方式：" not in prediction["forecastText"]


def test_course_history_is_explained_without_changing_public_marks():
    detail = race("地方")
    detail["distance"] = 1500
    detail["horses"][0]["allPastRuns"] = [
        {"date": "2026-10-15", "finish": 1, "fieldSize": 10,
         "track": "大井", "distance": 1500, "passing": [1]},
    ]
    original = deepcopy(detail)
    p = build_prediction(detail, now=NOW)
    e = p["paceEvidence"]["historicalCourseEvidence"][1]
    assert e["sameTrackDistanceStarts"] == 1
    assert e["sameTrackDistanceWins"] == 1
    assert "同場・同距離で確認できた1走中1勝" in p["forecastText"]
    assert generate_marks(p)[0]["horseNumber"] == 1
    assert detail == original


def test_public_projection_contains_prediction_marks_and_bets_without_mutating_input():
    detail = race("地方")
    original = deepcopy(detail)
    published = with_preoff_clock(public_race, detail)
    assert published["predictionStatus"] == "ready"
    assert published["predictionMarks"]
    assert {x["mark"] for x in published["predictionMarks"]} == {"◎", "○", "▲", "△", "☆"}
    assert 1 <= sum(x["points"] for x in published["recommendedBets"]) <= 5
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
    assert 1 <= sum(x["points"] for x in enriched["recommendedBets"]) <= 5
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


def test_existing_server_seal_uses_stage64_marks_and_tickets_without_new_pipeline():
    from scripts.arvexq_freeze_predictions import prepare_seal, capture_original_bet
    from arvexq.prediction.prerace_archive import sealed_lock
    detail = race("地方")
    for i, horse in enumerate(detail["horses"], 1):
        horse["name"] = f"H{i}"
    original = deepcopy(detail)
    sealed = prepare_seal(detail, now=NOW)
    assert sealed["status"] == "sealed", sealed
    stored = sealed["detail"]
    assert detail == original
    assert sealed_lock(stored)
    assert stored["predictionModelVersion"] == "arvexq-stage64-product-v1"
    assert {m["mark"] for m in stored["predictionMarks"]} == {"◎", "○", "▲", "△", "☆"}
    lock_marks = {m["horseNumber"]: m["mark"] for m in stored["preRacePrediction"]["horses"]}
    assert {m["horseNumber"]: m["mark"] for m in stored["predictionMarks"]} == {
        n: m for n, m in lock_marks.items() if m}
    ticket = capture_original_bet(stored, NOW)
    assert ticket["items"] == stored["recommendedBets"]
    assert ticket["modelVersion"] == "arvexq-stage64-product-v1"
    assert ticket["fixedBeforePost"]
    from scripts.arvexq_prerace_bet_integrity import has_valid_original
    from arvexq.prediction.prerace_archive import post_at
    assert has_valid_original(ticket, race_id=detail["id"], start_at=post_at(detail))


def test_server_seal_does_not_backfill_after_post_or_missing_stage64_evidence():
    from scripts.arvexq_freeze_predictions import prepare_seal
    detail = race("地方")
    for i, horse in enumerate(detail["horses"], 1):
        horse["name"] = f"H{i}"
    later = datetime(2026, 10, 23, 13, 0, tzinfo=ZoneInfo("Asia/Tokyo"))
    assert prepare_seal(detail, now=later)["status"] == "started-no-new-lock"
    detail["horses"][0]["recentRaces"] = []
    assert prepare_seal(detail, now=NOW)["status"] == "incomplete-prediction"
    assert "preRacePrediction" not in detail


def test_stage64_seal_transport_retains_integer_probability_keys_losslessly():
    import json
    from scripts.arvexq_freeze_predictions import prepare_seal, encode_sealed_d1_sync_detail
    from arvexq.ingest.full_snapshot_codec import unpack_detail
    detail = race("地方")
    for i, horse in enumerate(detail["horses"], 1):
        horse["name"] = f"H{i}"
    sealed = prepare_seal(detail, now=NOW)
    assert sealed["status"] == "sealed"
    source = sealed["detail"]
    packed = encode_sealed_d1_sync_detail(source)
    restored = unpack_detail(packed)
    assert restored == json.loads(json.dumps(source, ensure_ascii=False))
    assert restored["predictionMarks"] == source["predictionMarks"]
    assert restored["recommendedBets"] == source["recommendedBets"]
    assert restored["preRacePrediction"] == source["preRacePrediction"]

def test_wager_portfolio_counts_only_new_finish_coverage():
    values = {"trifecta": [
        {"combo": [1, 2, 3], "probability": 0.55},
        {"combo": [2, 1, 3], "probability": 0.25},
        {"combo": [3, 2, 1], "probability": 0.20},
    ]}
    prediction = {"predictionStatus": "ready", "stages": {"probability": {"value": values}}}
    marks = [{"horseNumber": n, "mark": m} for n, m in
             [(1, "◎"), (2, "○"), (3, "▲")]]
    result = generate_tickets(prediction, marks)
    # All actual top-three sets are identical in this synthetic example:
    # buying the same complete coverage five times is not better than one.
    assert sum(entry["points"] for entry in result) == 1
    assert result[0]["kind"] == "3連複"
    assert result[0]["combos"] == [[1, 2, 3]]


def test_stage64_outputs_share_one_prediction_and_pace_explanation():
    source = race("地方")
    for h in source["horses"]:
        h["name"] = "馬" + str(h["horseNumber"])
    published = with_preoff_clock(public_race, source)
    forecast = published["forecastText"]
    model = published["prediction"]
    marks = published["predictionMarks"]
    tickets = published["recommendedBets"]
    assert model["forecastText"] == forecast
    assert model["modelVersion"] == published["predictionModelVersion"]
    assert str(marks[0]["horseNumber"]) in forecast
    assert "初角位置" in forecast and "逃げることは同義ではない" in forecast
    assert "確率校正は未完了" in forecast
    selected = {n for item in tickets for pair in item["combos"] for n in pair}
    assert selected.issubset({m["horseNumber"] for m in marks})
    assert len(model["stages"]) == 6



def test_saved_preoff_ticket_publication_uses_five_points_without_changing_archive():
    detail = race("地方")
    preoff = with_preoff_clock(public_race, detail)
    original = deepcopy(preoff)
    # Legacy archive remains stored unmodified, while its pre-off probability
    # evidence is safely projected into the current five-point recommendation.
    original["recommendedBets"] = [
        {"kind": "ワイド", "combos": [[1, 2], [1, 3], [1, 4], [1, 5], [2, 3]], "points": 5},
        {"kind": "馬連", "combos": [[1, 2], [1, 3], [1, 4], [1, 5], [2, 3]], "points": 5},
    ]
    archive = deepcopy(original)
    original["result"] = {"status": "確定", "finishers": [{"horseNumber": 1, "finish": 1}]}
    archive = deepcopy(original)
    projected = public_race(original)
    assert projected["predictionStatus"] == "ready"
    assert 1 <= sum(x["points"] for x in projected["recommendedBets"]) <= 5
    assert 1 <= sum(len(x["combos"]) for x in projected["recommendedBets"]) <= 5
    assert original == archive
    assert original["recommendedBets"] != projected["recommendedBets"]


def test_unsupported_front_competition_is_not_invented_in_either_circuit():
    for owner in ("中央", "地方"):
        p = build_prediction(race(owner), now=NOW)
        assert p is not None
        stages = p["stages"]
        evidence = p["paceEvidence"]
        assert evidence["source"] == "preoff-prior-first-corner-observations"
        assert evidence["actualLeadVerified"] is False
        assert evidence["actualPaceVerified"] is False
        assert evidence["scenarioOccurrenceCalibrated"] is False
        assert evidence["aiEnsembleTrained"] is False
        assert stages["pace"]["model"] == "no-unsupported-tactical-boost"
        assert len(stages["pace"]["value"]) == 1
        assert all(delta == 0 for delta in stages["pace"]["value"][0].values())
        assert set(stages) == {"ability","runningStyle","pace","probability","marks","tickets"}
        assert set(stages["pace"]["value"][0]) == set(stages["ability"]["value"])
