"""Different trained AI architectures with independent date/circuit gates."""
from datetime import date, timedelta
from copy import deepcopy

import pytest

from arvexq.prediction.fusion_ai_models import (
    fit_two_ais, predict_logistic, predict_bayes,
)

OFF = "2026-10-24T12:00:00+09:00"
CAPTURE = "2026-10-24T10:00:00+09:00"


def card(day="2026-10-24", result=False, circuit="地方"):
    race = {
        "id": ("nar" if circuit=="地方" else "jra")+"-"+day+"-園田-02",
        "date": day, "circuit": circuit,
        "track": "園田", "surface": "ダート", "distance": 1400,
        "startTime": "12:00",
        "horses": [{
            "horseNumber": n, "name": "テスト馬"+str(n),
            "recentRaces": [
                {"date": "2026-08-01", "finish": n, "fieldSize": 8,
                 "distance": 1400, "track": "園田", "surface": "ダート",
                 "cornerPositions": [n,n], "marginSeconds": .1*n},
                {"date": "2026-07-01", "finish": max(1, n-1), "fieldSize": 8,
                 "distance": 1200, "track": "園田", "surface": "ダート",
                 "cornerPositions": [n,n]},
            ],
        } for n in range(1,6)]}
    if result:
        race["result"] = {"status":"確定",
                          "finishers":[{"horseNumber":n,"finish":n} for n in range(1,6)]}
    return race


def samples():
    return [card((date(2026,9,1)+timedelta(days=i)).isoformat(),True)
            for i in range(30)]


def test_trained_pairwise_and_naive_bayes_are_distinct_and_both_have_order_probabilities():
    fitted=fit_two_ais(samples(),circuit="地方",target_date="2026-10-24")
    assert set(fitted)=={"ai:learned","ai:bayes"}
    assert fitted["ai:learned"]["version"]!=fitted["ai:bayes"]["version"]
    target=card()
    original=deepcopy(target)
    outputs={
        "ai:learned":predict_logistic(
            target,fitted["ai:learned"],captured_at=CAPTURE,scheduled_off_at=OFF),
        "ai:bayes":predict_bayes(
            target,fitted["ai:bayes"],captured_at=CAPTURE,scheduled_off_at=OFF),
    }
    assert target==original
    for name,output in outputs.items():
        assert output["modelVersion"].startswith(name+"/")
        assert output["modelTrainingThrough"]<target["date"]
        assert sum(output["win"].values())==pytest.approx(1)
        assert sum(output["top3"].values())==pytest.approx(3)
        assert sum(z["probability"] for z in output["trifecta"])==pytest.approx(1)


def test_both_ai_families_reject_target_results_late_capture_and_cross_circuit():
    fitted=fit_two_ais(samples(),circuit="地方",target_date="2026-10-24")
    for key,fn in (("ai:learned",predict_logistic),("ai:bayes",predict_bayes)):
        model=fitted[key]
        with pytest.raises(ValueError,match="post-off"):
            fn(card(),model,captured_at="2026-10-24T12:01:00+09:00",
               scheduled_off_at=OFF)
        with pytest.raises(ValueError,match="result"):
            fn(card(result=True),model,captured_at=CAPTURE,scheduled_off_at=OFF)
        with pytest.raises(ValueError,match="circuit"):
            fn(card(circuit="中央"),model,captured_at=CAPTURE,scheduled_off_at=OFF)


def test_actual_debutants_are_unknown_observations_not_hidden_as_failed_fields():
    past=samples()
    for race in past:
        race["horses"][-1]["recentRaces"]=[]
    fitted=fit_two_ais(past,circuit="地方",target_date="2026-10-24")
    current=card()
    current["horses"][-1]["recentRaces"]=[]
    for key,fn in (("ai:learned",predict_logistic),("ai:bayes",predict_bayes)):
        out=fn(current,fitted[key],captured_at=CAPTURE,scheduled_off_at=OFF)
        assert 5 in out["win"]
        assert out["win"][5]>0
        assert sum(out["win"].values())==pytest.approx(1)
        assert len(out["trifecta"])==5*4*3
    from arvexq.prediction.learned_scenarios import race_evidence
    runner=next(row for row in race_evidence(current) if row["horseNumber"]==5)
    assert runner["observedStarts"]==0
    assert runner["sourceDates"]==[]
