"""Existing D1/public/UI data contracts for the replacement empirical forecast.

All figures are synthetic contract fixtures, never claimed real racing results.
"""
from copy import deepcopy
from datetime import date, datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

from arvexq.prediction.empirical_fusion import fit_weights, blend, VERSION
from arvexq.prediction.mineta_public_pace import public_pace_factors
from arvexq.forecast.engine import build_prediction
from arvexq.forecast.publication import public_race
from arvexq.forecast.marks import generate_marks
from arvexq.forecast.tickets import generate_tickets
from scripts.arvexq_freeze_predictions import prepare_seal, capture_original_bet

METHODS = ("mineta", "expert:position", "expert:course", "ai:learned", "ai:mass")
TARGET = "2026-10-28"
NOW = datetime(2026, 10, 27, 10, 0, tzinfo=ZoneInfo("Asia/Tokyo"))


def opinion(name, day, race_id):
    return {
        "modelVersion": name + "/v1", "evidenceId": race_id + "/" + name,
        "raceId": race_id, "capturedAt": day + "T09:00:00+09:00",
        "win": {i: 0.6 if i == 1 else 0.1 for i in range(1, 6)},
        "top3": {i: .6 for i in range(1, 6)},
        "stakeYen": 100, "returnYen": 150 if name == "mineta" else 100,
    }


def calibration():
    rows = []
    for day_offset in range(30):
        day = (date(2026, 9, 1) + timedelta(days=day_offset)).isoformat()
        race_id = "nar-" + day + "-園田-01"
        rows.append({
            "raceDate": day, "raceId": race_id, "circuit": "地方",
            "capturedAt": day + "T09:00:00+09:00",
            "scheduledOffAt": day + "T12:00:00+09:00",
            "finishers": [1, 2, 3], "roster": [1, 2, 3, 4, 5],
            "arms": {name: opinion(name, day, race_id) for name in METHODS},
        })
    return fit_weights(rows, target_date=TARGET)


def fixture(with_quotes=True):
    race_id = "nar-" + TARGET + "-園田-01"
    opinions = {name: opinion(name, "2026-10-27", race_id) for name in METHODS}
    # Actual recorded event distribution; top-three and win marginals are
    # recomputed below so an impossible sample cannot masquerade as calibrated.
    orders = [
        ([1, 2, 3], .6), ([2, 3, 4], .1), ([3, 4, 5], .1),
        ([4, 5, 1], .1), ([5, 1, 2], .1),
    ]
    top3 = {i: sum(p for combo, p in orders if i in combo) for i in range(1,6)}
    for arm in opinions.values():
        arm["trifecta"] = [{"combo": combo, "probability": p} for combo,p in orders]
        arm["top3"] = top3
    detail = {
        "id": race_id, "date": TARGET, "circuit": "地方",
        "track": "園田", "surface": "ダート", "analysisMode": "平地",
        "distance": 1400, "fieldSize": 5, "startTime": "12:00",
        "horses": [
            {"horseNumber": i, "name": "試験馬" + str(i),
             "recentRaces": [{"date": "2026-10-20", "distance": 1400,
                 "track": "園田", "surface": "ダート", "fieldSize": 6,
                 "finish": i, "cornerPositions": [i, i]}]}
            for i in range(1, 6)],
        "fusionInputs": {"opinions": opinions, "calibration": calibration()},
    }
    if with_quotes:
        detail["fusionInputs"]["odds"] = {
            "sourceKind": "official_preoff_quotes",
            "capturedAt": "2026-10-27T10:00:00+09:00",
            "prices": [{"kind": "馬連", "combo": [1,2], "odds": 2.5},
                       {"kind": "3連複", "combo": [1,2,3], "odds": 3.0},
                       {"kind": "3連単", "combo": [1,2,3], "odds": 4.0}],
        }
    return detail


def patch_time(call, detail):
    with patch("arvexq.forecast.engine.datetime") as clock:
        clock.now.return_value = NOW
        clock.fromisoformat.side_effect = datetime.fromisoformat
        return call(detail)


def test_six_stages_mark_ticket_public_projection_and_no_mutation():
    src = fixture()
    saved = deepcopy(src)
    assert public_pace_factors(src)["raceId"] == src["id"]
    raw = blend(src, src["fusionInputs"]["opinions"],
                src["fusionInputs"]["calibration"],
                quoted_odds=src["fusionInputs"]["odds"])
    assert raw["predictionMarks"]
    output = build_prediction(src, now=NOW)
    assert src == saved
    assert output is not None, "complete preoff inputs must produce an output"
    assert output["modelVersion"] == VERSION
    baseline = output["stages"]["pace"]["value"]["fourPhaseHistoricalBaseline"]
    assert set(baseline) == {str(i) for i in range(1, 6)}
    assert output["stages"]["pace"]["value"]["fourPhaseBaselineValidated"] is False
    assert baseline["1"]["start"]["projectedRank"] is None
    assert baseline["1"]["thirdCorner"]["projectedRank"] is None
    assert baseline["1"]["straight"]["projectedRank"] == 1.0
    assert output["predictionMarks"] == raw["predictionMarks"]
    ability = output["stages"]["ability"]
    assert ability["probabilityCalibrationVerified"] is False
    assert set(ability["modelVersions"]) == set(METHODS)
    assert set(ability["value"]) == {str(i) for i in range(1, 6)}
    assert ability["value"]["1"]["recentRuns"] == 1
    assert ability["value"]["1"]["recentTop3Rate"] == 1.0
    assert ability["value"]["1"]["fullCareerRuns"] == 1
    assert ability["value"]["1"]["careerTop3Rate"] == 1.0
    assert ability["value"]["1"]["careerPeakFinishQuality"] == 1.0
    assert ability["value"]["1"]["careerConsistency"] is None
    assert ability["value"]["1"]["classEvidenceRuns"] == 0
    assert ability["value"]["1"]["sectionalEvidenceRuns"] == 0
    assert ability["value"]["1"]["representativeComparable"]["finish"] == 1
    assert ability["value"]["1"]["sameDistanceQuality"] == 1.0
    assert ability["value"]["1"]["opponentLevelMean"] is None
    assert ability["value"]["1"]["marginMean"] is None
    assert output["humanOverrideAllowed"] is False
    assert set(output["stages"]) == {
        "ability","runningStyle","pace","probability","marks","tickets"}
    assert {x["mark"] for x in generate_marks(output)} == {"◎","○","▲","△","☆"}
    bets = generate_tickets(output, generate_marks(output), race=src)
    assert bets
    assert 1 <= sum(x["points"] for x in bets) <= 5
    projected = patch_time(public_race, src)
    assert projected["predictionStatus"] == "ready"
    assert projected["predictionModelVersion"] == VERSION
    assert projected["predictionMarks"] == generate_marks(output)
    assert projected["recommendedBets"] == bets
    marked = {row["horseNumber"] for row in projected["predictionMarks"]}
    assert set(projected["prediction"]["stages"]["pace"]["value"]["markOrder"]) == marked
    assert all(set(combo).issubset(marked)
               for ticket in projected["recommendedBets"]
               for combo in ticket["combos"])
    assert projected["prediction"]["paceEvidence"]["markLabels"]
    assert "fusionInputs" not in projected
    assert src == saved


def test_original_is_sealed_and_not_recreated_after_off():
    src = fixture()
    sealed = prepare_seal(src, now=NOW)
    assert sealed["status"] == "sealed", sealed
    saved = sealed["detail"]
    assert saved["predictionModelVersion"] == VERSION
    assert len(saved["predictionMarks"]) == 5
    bet = capture_original_bet(saved, NOW)
    assert bet["modelVersion"] == VERSION
    assert bet["fixedBeforePost"] is True
    assert bet["items"] == saved["recommendedBets"]
    after = patch_time(public_race, {
        **saved, "result": {"status":"確定",
                           "finishers":[{"horseNumber":1,"finish":1}]}})
    assert after["predictionMarks"] == saved["predictionMarks"]
    assert after["recommendedBets"] == saved["recommendedBets"]


def test_no_stored_independent_evidence_means_no_fake_prediction():
    empty = fixture()
    empty.pop("fusionInputs")
    assert build_prediction(empty, now=NOW) is None
    published = patch_time(public_race, empty)
    assert published["predictionStatus"] == "disabled"
    assert not published.get("predictionMarks")
    missing_odds = fixture(with_quotes=False)
    out = build_prediction(missing_odds, now=NOW)
    assert out is not None
    assert generate_marks(out)
    assert generate_tickets(out, generate_marks(out)) == []
    lock = prepare_seal(missing_odds, now=NOW)
    assert lock["status"] == "sealed"
    bet = capture_original_bet(lock["detail"], NOW)
    assert bet["decision"] == "見送り"
    assert bet["items"] == []
