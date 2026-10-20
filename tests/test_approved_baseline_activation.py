"""User withdrew approval for the assistant-created baseline forecast."""
from copy import deepcopy

from pathlib import Path
from arvexq.forecast.publication import public_race

def example():
    return {"id":"race", "date":"2099-12-31", "startTime":"18:30",
            "horses":[{"horseNumber":i,"name":str(i),
                       "recentRaces":[{"finish":1},{"finish":2},{"finish":3}]}
                      for i in range(1,6)]}

def test_rejected_assistant_forecast_does_not_generate_anything():
    facts=example();original=deepcopy(facts)
    assert not (Path(__file__).resolve().parents[1] / "arvexq/forecast/engine.py").exists()
    assert facts == original

def test_publication_strips_past_and_new_unapproved_marks():
    detail=example()
    detail["predictionMarks"]=[{"horseNumber":1,"mark":"◎"}]
    detail["horses"][0]["mark"]="◎"
    detail["preRaceBet"]={"items":[[1,2]]}
    result=public_race(detail)
    assert result["predictionStatus"]=="disabled"
    assert "predictionMarks" not in result
    assert "preRaceBet" not in result
    assert all("mark" not in horse for horse in result["horses"])
    assert "predictionModelVersion" not in result
    assert detail["horses"][0]["mark"]=="◎"
