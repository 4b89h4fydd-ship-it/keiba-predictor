from itertools import permutations
from arvexq.forecast.probability_contract import summarize_joint_top3


def rows(numbers):
    triples = list(permutations(numbers, 3))
    return [{"horseNumbers": list(t), "probability": 1 / len(triples)} for t in triples]


def test_full_three_runner_distribution_is_valid():
    result = summarize_joint_top3(rows([3, 1, 2]), [3, 1, 2])
    assert result is not None
    assert [x["horseNumber"] for x in result["horses"]] == [1, 2, 3]
    assert all(abs(x["winProbability"] - 1 / 3) < 1e-9 for x in result["horses"])
    assert all(abs(x["top3Probability"] - 1.0) < 1e-9 for x in result["horses"])
    assert "approvedForProduction" not in result


def test_missing_triple_and_duplicate_triple_fail_closed():
    data = rows([1, 2, 3, 4])
    assert summarize_joint_top3(data[:-1], [1, 2, 3, 4]) is None
    data[-1] = data[0].copy()
    assert summarize_joint_top3(data, [1, 2, 3, 4]) is None


def test_invalid_mass_and_nonstarter_fail_closed():
    data = rows([1, 2, 3])
    data[0]["probability"] = 0.7
    assert summarize_joint_top3(data, [1, 2, 3]) is None
    data = rows([1, 2, 3])
    data[0]["horseNumbers"][0] = 99
    assert summarize_joint_top3(data, [1, 2, 3]) is None
    assert summarize_joint_top3(rows([1, 2, 3]), [1, 1, 3]) is None
