from arvexq.diagnosis import diagnose_horse
from arvexq.history import recent_runs
from arvexq.horse_detail import build_horse_detail


def _horse():
    runs = [
        {
            "date": f"2026-01-{i:02d}",
            "track": "大井",
            "title": "テストレース",
            "surface": "ダート",
            "distance": 1200,
            "condition": "良",
            "finish": (i % 6) + 1,
            "time": "1:10.0",
            "passing": "",
            "last3f": 36.0,
            "first1f": 12.0,
            "carriedWeight": 55.0,
            "bodyWeight": 480,
            "fieldSize": 12,
            "opponentLevel": "B",
            "index": 70,
        }
        for i in range(1, 9)
    ]
    return {"horseNumber": 1, "name": "テストホース", "recentRaces": runs}


def test_career_analysis_uses_all_observed_runs():
    horse = _horse()
    race = {"track": "大井", "surface": "ダート", "distance": 1200, "date": "2026-02-01", "horses": [horse]}
    detail = build_horse_detail(horse, race)
    assert len(detail["recentFive"]) == 5
    assert detail["careerAnalysis"]["total_runs"] == 8


def test_diagnosis_includes_career_analysis():
    horse = _horse()
    race = {"track": "大井", "surface": "ダート", "distance": 1200, "date": "2026-02-01", "horses": [horse]}
    view = diagnose_horse(horse, race)
    assert view["careerAnalysis"]["analyzed_runs"] == 8


def test_missing_history_is_flagged():
    horse = {
        "horseNumber": 1,
        "name": "テストホース",
        "recentRaces": [{"date": "2026-01-01", "finish": 1}],
    }
    race = {"track": "大井", "surface": "ダート", "distance": 1200, "date": "2026-02-01", "horses": [horse]}
    detail = build_horse_detail(horse, race)
    assert detail["careerAnalysis"]["data_limitation"] == "partial"