"""Historical 30-race end-to-end replay: official payouts not target features."""
from copy import deepcopy
from datetime import date,timedelta

import pytest

from arvexq.prediction.fusion_historical_replay import train_and_validate


def card(day, circuit="地方", winner=1):
    rid=("nar" if circuit=="地方" else "jra")+"-"+day+"-園田-01"
    order=[winner]+[n for n in range(1,6) if n!=winner]
    horses=[{
        "horseNumber":n,"name":"馬"+str(n),
        "recentRaces":[
            {"date":"2026-06-01","finish":n,"fieldSize":8,
             "distance":1400,"track":"園田","surface":"ダート",
             "cornerPositions":[n,n],"marginSeconds":n*.1},
            {"date":"2026-05-01","finish":max(1,n-1),"fieldSize":8,
             "distance":1200,"track":"園田","surface":"ダート",
             "cornerPositions":[n,n]},
        ]} for n in range(1,6)]
    return {
        "id":rid,"date":day,"circuit":circuit,"track":"園田",
        "surface":"ダート","distance":1400,"startTime":"12:00",
        "analysisMode":"平地","horses":horses,
        "result":{
            "status":"確定",
            "finishers":[{"horseNumber":n,"finish":i+1} for i,n in enumerate(order)],
            "payouts":[{"type":"単勝","combination":str(winner),
                        "amount":320 if winner==1 else 820}],
        }
    }


def sixty():
    return [card((date(2026,7,1)+timedelta(days=i)).isoformat()) for i in range(60)]


def test_real_time_split_30_plus_30_without_retroactively_sealed_picks():
    source=sixty()
    old=deepcopy(source)
    result=train_and_validate(source,circuit="地方",target_date="2026-10-24")
    assert source==old
    audit=result["audit"]
    assert audit["trainingRaces"]>=30
    assert audit["validationRaces"]>=30
    assert audit["trainingThrough"]<audit["validationThrough"]<"2026-10-24"
    assert audit["notActualOriginalPreoffCapture"] is True
    assert audit["noTargetRaceResultUsed"] is True
    fitted=result["calibration"]
    assert fitted["nRaces"]>=30
    assert fitted["calibrationMethod"]=="chronological-replay-not-original-frozen"
    assert fitted["notActualPreoffReceipts"] is True
    assert len(fitted["weights"])==5
    assert set(fitted["weights"])=={
        "mineta","expert:form","expert:course","ai:learned","ai:bayes"}
    assert sum(fitted["weights"].values())==pytest.approx(1)
    assert fitted["metrics"]["mineta"]["stakeYen"]==100*fitted["nRaces"]
    assert fitted["metrics"]["mineta"]["returnYen"]>=0


def test_no_large_enough_holdout_fails_instead_of_backfilling_results():
    with pytest.raises(ValueError,match="insufficient"):
        train_and_validate(sixty()[:35],circuit="地方",target_date="2026-10-24")
    with pytest.raises(ValueError,match="separate"):
        train_and_validate(sixty(),circuit="混合",target_date="2026-10-24")
