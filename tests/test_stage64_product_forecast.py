"""Replacement production boundary and immutable legacy archive contracts.

Stage64 research has independent archive/replay tests. It MUST NOT remain the
active forecast model merely so obsolete Stage64 product tests keep passing.
The new complete fusion chain is verified in test_empirical_fusion_live_contract.
"""
from copy import deepcopy
from datetime import datetime
from zoneinfo import ZoneInfo

from arvexq.forecast.engine import build_prediction, VERSION
from arvexq.forecast.publication import public_race

OLD = "arvexq-stage64-product-v1"


def race(circuit="地方"):
    prefix = "nar" if circuit == "地方" else "jra"
    return {"id": f"{prefix}-2026-10-28-試験場-01",
            "date": "2026-10-28", "startTime": "12:00", "fieldSize": 5,
            "circuit": circuit, "track": "試験場",
            "surface": "芝" if circuit == "中央" else "ダート",
            "horses": [
                {"horseNumber": no, "recentRaces": [
                    {"date": "2026-10-20", "finish": no,
                     "fieldSize": 5, "cornerPositions": [no]}]}
                for no in range(1, 6)]}


def test_stage64_is_not_the_active_preoff_forecast():
    now = datetime(2026, 10, 27, 9, 0, tzinfo=ZoneInfo("Asia/Tokyo"))
    assert VERSION == "arvexq-empirical-fusion-v1"
    for circuit in ("中央", "地方"):
        detail = race(circuit)
        untouched = deepcopy(detail)
        assert build_prediction(detail, now=now) is None
        assert detail == untouched


def test_missing_independent_method_records_never_trigger_old_fallback():
    detail = race()
    detail["predictionStatus"] = "disabled"
    detail["predictionModelVersion"] = OLD
    result = public_race(detail)
    assert result["predictionStatus"] == "disabled"
    assert "predictionMarks" not in result
    assert "recommendedBets" not in result


def test_only_verified_old_original_is_preserved_for_historical_readback():
    detail = race()
    labels = ("◎", "○", "▲", "△", "☆")
    detail["predictionStatus"] = "ready"
    detail["predictionModelVersion"] = OLD
    detail["prediction"] = {
        "modelVersion": OLD, "predictionStatus": "ready",
        "productionEligible": True, "raceId": detail["id"],
        "date": detail["date"], "forecastText": "発走前に保存された旧方式の観測根拠"}
    detail["predictionMarks"] = [
        {"horseNumber": n, "mark": mark}
        for n, mark in enumerate(labels, 1)]
    detail["recommendedBets"] = [{
        "kind":"ワイド", "combos": [[1, 2]], "points": 1,
        "reason": "過去の保存原本"}]
    detail["result"] = {
        "status": "確定", "finishers": [{"horseNumber": 1, "finish": 1}]}
    original = deepcopy(detail)
    published = public_race(detail)
    assert detail == original
    assert published["predictionMarks"] == original["predictionMarks"]
    assert published["recommendedBets"] == original["recommendedBets"]
    assert published["predictionModelVersion"] == OLD
    assert published["forecastText"] == original["prediction"]["forecastText"]


def test_incomplete_legacy_original_cannot_be_upgraded_after_off():
    detail = race()
    detail["result"] = {"status": "確定"}
    detail["predictionStatus"] = "ready"
    detail["predictionModelVersion"] = OLD
    detail["prediction"] = {"modelVersion": OLD}
    projected = public_race(detail)
    assert projected["predictionStatus"] == "disabled"
    assert "predictionMarks" not in projected
