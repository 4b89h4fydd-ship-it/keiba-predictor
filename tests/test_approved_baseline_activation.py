"""User withdrew approval for the assistant-created baseline forecast."""
from copy import deepcopy
from datetime import datetime
from zoneinfo import ZoneInfo

from arvexq.forecast.engine import build_prediction
from arvexq.forecast.marks import generate_marks
from arvexq.forecast.tickets import generate_tickets
from arvexq.forecast.publication import public_race

def example():
    return {"id":"race", "date":"2099-12-31", "startTime":"18:30",
            "horses":[{"horseNumber":i,"name":str(i),
                       "recentRaces":[{"finish":1},{"finish":2},{"finish":3}]}
                      for i in range(1,6)]}

def test_rejected_assistant_forecast_does_not_generate_anything():
    facts=example();original=deepcopy(facts)
    assert build_prediction(facts,now=datetime(2099,12,31,10,tzinfo=ZoneInfo("Asia/Tokyo"))) is None
    assert generate_marks({"scenarios":[([1,2,3],1.0)]}) == []
    assert generate_tickets({"scenarios":[([1,2,3],1.0)]},[{"horseNumber":1}],quoted_odds={"mock":2}) == []
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
