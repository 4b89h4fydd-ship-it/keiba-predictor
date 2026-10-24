"""Winner-decision regression on the existing six-stage JRA/NAR pipeline.

These are synthetic contract tests, not evidence of a higher win hit rate.
"""
from copy import deepcopy
from datetime import datetime
from zoneinfo import ZoneInfo

from arvexq.research.stage64.pipeline import predict
from arvexq.forecast.engine import build_prediction
from arvexq.forecast.marks import generate_marks
from arvexq.forecast.tickets import generate_tickets


def race(circuit="nar"):
    track = "園田" if circuit == "nar" else "京都"
    surface = "ダート" if circuit == "nar" else "芝"

    def run(day, finish, distance, margin, no):
        return {"date": day, "track": track, "raceNumber": 3, "surface": surface,
                "distance": distance, "fieldSize": 6, "finish": finish,
                "cornerPositions": [no, no], "marginSeconds": margin,
                "opponentLevel": .7}

    return {
        "id": f"{circuit}-2026-10-28-{track}-03",
        "date": "2026-10-28", "circuit": circuit,
        "track": track, "surface": surface, "analysisMode": "平地",
        "distance": 1400, "fieldSize": 4, "startTime": "12:30",
        "horses": [
            {"horseNumber": 1, "recentRaces": [
                run("2026-10-15", 2, 1400, .30, 2),
                run("2026-10-08", 1, 1200, .00, 1),
                run("2026-10-01", 1, 1200, .00, 1),
            ]},
            {"horseNumber": 2, "recentRaces": [
                run("2026-10-15", 1, 1400, .00, 1),
                run("2026-10-08", 4, 1600, .60, 4),
                run("2026-10-01", 4, 1600, .60, 4),
            ]},
            {"horseNumber": 3, "recentRaces": [
                run("2026-10-15", 5, 1400, .80, 5),
                run("2026-10-08", 5, 1200, .80, 5),
            ]},
            {"horseNumber": 4, "recentRaces": [
                run("2026-10-15", 6, 1400, 1.00, 6),
                run("2026-10-08", 6, 1200, 1.00, 6),
            ]},
        ],
    }


def test_confirmed_nar_rival_rewrites_win_probability_marks_and_tickets():
    source = race("nar")
    original = deepcopy(source)
    result = predict(source, expected_circuit="nar")
    assert source == original
    decision = result["winnerEvidenceComparison"]
    assert decision["originalWinnerHorseNumber"] == 1
    assert decision["selectedWinnerHorseNumber"] == 2
    assert decision["appliedToWinProbabilityAndMarks"] is True
    assert decision["winnerRankUnchanged"] is False
    assert result["stages"]["marks"]["value"]["orderedWinCandidates"][0] == 2
    win = result["stages"]["probability"]["value"]["win"]
    assert max(win, key=win.get) == 2
    assert len(result["stages"]) == 6
    assert result["productionEligible"] is False

    published = build_prediction(source, now=datetime(
        2026, 10, 27, 9, 0, tzinfo=ZoneInfo("Asia/Tokyo")))
    assert published["predictionStatus"] == "ready"
    assert generate_marks(published)[0]["horseNumber"] == 2
    assert generate_marks(published)[0]["mark"] == "◎"
    assert "◎判定へ反映" in published["forecastText"]
    items = generate_tickets(published, generate_marks(published))
    assert 1 <= sum(item["points"] for item in items) <= 5


def test_incomplete_or_contradictory_rematch_does_not_replace_winner():
    for mod in ("no-matching-margin", "rematch-loss", "future-only"):
        source = race("nar")
        if mod == "no-matching-margin":
            source["horses"][1]["recentRaces"][0].pop("marginSeconds")
        elif mod == "rematch-loss":
            source["horses"][0]["recentRaces"][1]["distance"] = 1400
            source["horses"][0]["recentRaces"][1]["raceNumber"] = 3
            source["horses"][1]["recentRaces"][1]["distance"] = 1400
            source["horses"][1]["recentRaces"][1]["raceNumber"] = 3
            source["horses"][0]["recentRaces"][1]["finish"] = 1
            source["horses"][1]["recentRaces"][1]["finish"] = 4
        else:
            source["horses"][1]["recentRaces"][0]["date"] = "2026-10-29"
        out = predict(source, expected_circuit="nar")
        assert not out["winnerEvidenceComparison"]["appliedToWinProbabilityAndMarks"]
        assert out["stages"]["marks"]["value"]["orderedWinCandidates"][0] == 1


def test_jra_remains_independent_of_nar_head_to_head_override():
    source = race("jra")
    out = predict(source, expected_circuit="jra")
    assert out["winnerEvidenceComparison"]["method"] == "jra-course-distance-opposition-review"
    assert out["winnerEvidenceComparison"]["appliedToWinProbabilityAndMarks"] is False
    assert out["stages"]["marks"]["value"]["orderedWinCandidates"][0] == 1
