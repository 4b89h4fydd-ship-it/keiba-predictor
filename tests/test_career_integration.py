from arvexq.diagnosis import diagnose_horse
from arvexq.history import all_runs, recent_runs
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


def test_all_runs_exposes_full_career():
    horse = _horse()
    assert len(all_runs(horse)) == 8
    assert len(recent_runs(horse)) == 5
    detail = build_horse_detail(horse)
    assert len(detail["recentFive"]) == 5
    assert detail["careerAnalysis"]["total_runs"] == 8


def test_diagnosis_includes_career_analysis():
    horse = _horse()
    race = {"track": "大井", "surface": "ダート", "distance": 1200, "horses": [horse]}
    view = diagnose_horse(horse, race)
    assert view["careerAnalysis"]["analyzed_runs"] == 8


def test_missing_history_is_flagged():
    horse = {
        "horseNumber": 1,
        "name": "テストホース",
        "recentRaces": [{"date": "2026-01-01", "finish": 1}],
    }
    detail = build_horse_detail(horse)
    assert detail["careerAnalysis"]["data_limitation"] == "partial"