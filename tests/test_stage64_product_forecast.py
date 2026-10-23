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
    published = public_race(detail)
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
    compact = _compact_display_snapshot(race("中央"))
    assert compact["predictionStatus"] == "ready"
    assert compact["predictionModelVersion"] == "arvexq-stage64-product-v1"
    assert compact["predictionMarks"]
    assert compact["recommendedBets"]
