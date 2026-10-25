"""Regression checks: six-stage receipt-only prediction publication."""
from pathlib import Path
from arvexq.forecast.publication import public_race

ROOT = Path(__file__).resolve().parents[1]


def test_no_unverified_forecast_fallback():
    race = {
        "id": "nar-20261027-test-1", "date": "2026-10-27",
        "circuit": "地方", "track": "大井", "startTime": "12:00",
        "horses": [{"horseNumber": i, "name": f"horse{i}"} for i in range(1, 9)],
        "fusionInputs": {"opinions": {}, "calibration": {}},
    }
    original = dict(race)
    result = public_race(race)
    assert result["predictionStatus"] == "disabled"
    assert not result.get("predictionMarks")
    assert not result.get("recommendedBets")
    assert race == original


def test_six_stage_ui_includes_safe_statuses():
    js = (ROOT / "arvexq/ui/static/app.js").read_text(encoding="utf-8")
    assert "新方式・6段階分析" in js
    assert "未適用・検証待ち" in js
    assert "未算出・未校正" in js
    assert "見送り（条件未充足" in js
    assert "sixStageAnalysisPanel(r)+content" in js


def test_newcomers_are_not_mixed_with_flat_jumps_or_banei():
    from arvexq.prediction.learned_scenarios import race_family
    base = {"track": "東京", "surface": "芝", "title": "1勝クラス"}
    assert race_family(base) == "flat"
    assert race_family(dict(base, title="2歳新馬")) == "debut"
    assert race_family(dict(base, analysisMode="新馬")) == "debut"
    assert race_family(dict(base, surface="障害", title="障害未勝利")) == "jumps"
    assert race_family(dict(base, track="帯広")) == "banei"
