"""Independent rank-distribution arithmetic and label integrity checks."""
from math import isclose
import pytest
from arvexq.forecast.top_three_joint_research import joint_top_three, evaluate_orders


def model(rows, rid="nar-test"):
    return {"raceId":rid,"status":"research-only-uncalibrated",
            "rows":[{"horseNumber":i,"winProbability":v} for i,v in rows]}


def test_three_runners_exact_podium_probabilities_and_marginals():
    pred=model([(1,.5),(2,.3),(3,.2)])
    out=joint_top_three(pred)
    assert len(out["orderedTopThree"])==6
    by={(r["first"],r["second"],r["third"]):r["probability"]
        for r in out["orderedTopThree"]}
    assert isclose(by[(1,2,3)],.5*(.3/.5))
    assert isclose(sum(by.values()),1.)
    marg={r["horseNumber"]:r for r in out["marginals"]}
    assert isclose(marg[1]["firstProbability"],.5)
    assert all(isclose(r["topThreeProbability"],1.) for r in out["marginals"])
    for key in ("firstProbability","secondProbability","thirdProbability"):
        assert isclose(sum(r[key] for r in out["marginals"]),1.)


def test_four_runners_exact_marginals_and_no_duplicate_finishers():
    result=joint_top_three(model([(1,.4),(2,.3),(3,.2),(4,.1)]))
    assert len(result["orderedTopThree"])==24
    assert all(len({x["first"],x["second"],x["third"]})==3
               for x in result["orderedTopThree"])
    assert isclose(sum(x["topThreeProbability"] for x in result["marginals"]),3.)
    assert result["promotionEligible"] is False


def test_permutation_invariance_of_marginals():
    a=joint_top_three(model([(1,.48),(2,.32),(3,.12),(4,.08)]))
    b=joint_top_three(model([(4,.08),(2,.32),(1,.48),(3,.12)]))
    for key in ("firstProbability","secondProbability","thirdProbability","topThreeProbability"):
        x={r["horseNumber"]:r[key] for r in a["marginals"]}
        y={r["horseNumber"]:r[key] for r in b["marginals"]}
        assert all(isclose(x[n],y[n],abs_tol=1e-12) for n in x)


@pytest.mark.parametrize("bad",[
    [(1,.5),(1,.3),(2,.2)],
    [(1,.5),(2,.5),(3,0.)],
    [(1,.5),(2,.3),(3,.3)],
    [(1,.5),(2,float("nan")),(3,.5)],
    [(1,True),(2,.3),(3,.7)],
])
def test_bad_field_fail_closed(bad):
    with pytest.raises(ValueError):
        joint_top_three(model(bad))


def test_rejects_production_or_untrusted_prediction():
    p=model([(1,.5),(2,.3),(3,.2)])
    p["status"]="production"
    with pytest.raises(ValueError):
        joint_top_three(p)


def test_order_metric_matches_exact_finish_label_and_prevents_identity_mixing():
    pred=model([(1,.5),(2,.3),(3,.2)])
    race={"raceId":"nar-test","horses":[
        {"horseNumber":1,"finish":1},{"horseNumber":2,"finish":2},
        {"horseNumber":3,"finish":3}]}
    out=evaluate_orders([pred],[race])
    assert out["top1Rate"]==1
    assert out["unorderedTopThreeSetRate"]==1
    assert out["orderedTopThreeRate"]==1
    assert out["exactOrderLogLoss"]>out["firstLogLoss"]
    with pytest.raises(ValueError,match="identity"):
        evaluate_orders([pred],[dict(race,raceId="unrelated")])


def test_incomplete_or_tied_result_rejected():
    pred=model([(1,.5),(2,.3),(3,.2)])
    race={"raceId":"nar-test","horses":[
        {"horseNumber":1,"finish":1},{"horseNumber":2,"finish":1},
        {"horseNumber":3,"finish":3}]}
    with pytest.raises(ValueError):
        evaluate_orders([pred],[race])
