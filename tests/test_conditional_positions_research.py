"""Regression tests for supervised second/third stage and leakage barriers."""
from copy import deepcopy
from datetime import date,timedelta
from math import isclose

import pytest

from arvexq.forecast.race_softmax_research import train,predict
from arvexq.forecast.conditional_positions_research import (
    train_positions,predict_positions,compare_holdout)
from arvexq.forecast.top_three_joint_research import joint_top_three
from tests.test_race_softmax_research import make_race


def training():
    return [make_race((date(2026,8,1)+timedelta(days=i)).isoformat(),
                      winner=(i%4)+1) for i in range(8)]


def test_train_positions_keeps_first_place_model_and_joint_normalized():
    races=training()
    win=train(races,epochs=8)
    before=deepcopy(win)
    position=train_positions(races,win,epochs=12)
    next_race=make_race("2026-08-15")
    result=predict_positions(position,win,next_race)
    assert win==before
    assert position["promotionEligible"] is False
    assert len(result["orderedTopThree"])==24
    assert isclose(sum(x["probability"] for x in result["orderedTopThree"]),1.)
    base=predict(win,next_race)
    a={x["horseNumber"]:x["firstProbability"] for x in result["marginals"]}
    b={x["horseNumber"]:x["winProbability"] for x in base["rows"]}
    assert all(isclose(a[i],b[i],abs_tol=1e-12) for i in a)
    for key in ("firstProbability","secondProbability","thirdProbability"):
        assert isclose(sum(r[key] for r in result["marginals"]),1.)
    assert "mark" not in str(result) and "bet" not in str(result)


def test_test_labels_never_affect_conditional_predictions():
    races=training()
    win=train(races,epochs=5)
    position=train_positions(races,win,epochs=5)
    a=make_race("2026-08-16")
    b=deepcopy(a)
    b["horses"][0]["finish"],b["horses"][1]["finish"]=2,1
    assert predict_positions(position,win,a)==predict_positions(position,win,b)


def test_train_and_model_identity_guard():
    races=training()
    win=train(races,epochs=5)
    position=train_positions(races,win,epochs=5)
    with pytest.raises(ValueError,match="lookahead"):
        predict_positions(position,win,races[0])
    tampered=deepcopy(position)
    tampered["secondWeights"][0]+=1
    with pytest.raises(ValueError,match="integrity"):
        predict_positions(tampered,win,make_race("2026-08-17"))
    tampered=deepcopy(position)
    tampered["winModelHash"]="another"
    with pytest.raises(ValueError):
        predict_positions(tampered,win,make_race("2026-08-17"))
    with pytest.raises(ValueError,match="strict"):
        bad=deepcopy(races)
        bad[0]["horses"][0]["finish"]=2
        train_positions(bad,win,epochs=5)


def test_comparison_never_automatically_promotes():
    races=training()
    win=train(races,epochs=5)
    position=train_positions(races,win,epochs=5)
    later=[make_race("2026-08-15"),make_race("2026-08-16")]
    report=compare_holdout(later,win,position)
    assert report["races"]==2
    assert report["promotionEligible"] is False
    assert report["modelSelection"]=="not-performed"
    assert report["candidate"]["firstLogLoss"]==pytest.approx(report["baseline"]["firstLogLoss"])
    assert report["candidate"]["exactOrderLogLoss"]>=0


def test_cross_circuit_and_repeated_training_rejected():
    races=training()
    win=train(races,epochs=5)
    with pytest.raises(ValueError,match="duplicate"):
        train_positions(races+[races[0]],win,epochs=5)
    changed=deepcopy(races)
    changed[0]["circuit"]="地方"
    with pytest.raises(ValueError,match="cross-circuit"):
        train_positions(changed,win,epochs=5)
