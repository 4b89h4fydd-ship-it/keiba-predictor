"""The assistant-created provisional forecasts may no longer be published."""
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
from arvexq.forecast.publication import public_race

JST=ZoneInfo("Asia/Tokyo")
def future_race():
    return {"id":"unapproved", "date":(datetime.now(JST)+timedelta(days=1)).date().isoformat(),
            "startTime":"23:59", "circuit":"地方","track":"園田",
            "predictionStatus":"provisional",
            "predictionMarks":[{"horseNumber":1,"mark":"◎"}],
            "horses":[{"horseNumber":i,"name":"X",
                       "mark":"◎","recentRaces":[{"finish":1} for _ in range(5)]}
                      for i in range(1,6)]}

def test_published_race_never_generates_unapproved_forecasts():
    data=future_race()
    output=public_race(data)
    assert output["predictionStatus"]=="disabled"
    assert "predictionMarks" not in output
    assert "predictionModelVersion" not in output
    assert "predictionEvidence" not in output
    assert "recommendedBets" not in output
    assert all("mark" not in h and "modelProbabilities" not in h for h in output["horses"])
    assert data["horses"][0]["mark"]=="◎"
