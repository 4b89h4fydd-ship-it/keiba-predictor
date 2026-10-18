"""Holdout rejects all future labels, incomplete fields, and tiny samples."""
from datetime import datetime, timedelta, timezone
import pytest

from arvexq.forecast.preoff_capture import capture_preoff_features
from arvexq.forecast.preoff_evidence_store import open_store, append_capture
from arvexq.forecast.verified_holdout import (
    build_verified_races, evaluate_verified_circuits, _validated_results,
)

JST = timezone(timedelta(hours=9))


def sample(day, circuit="中央"):
    detail = {"id": f"{circuit}-{day}-01", "date": day,
              "startTime": "12:00", "circuit": circuit, "track": "東京",
              "surface": "芝", "distance": 1600, "condition": "良",
              "horses": [
                  {"horseNumber": n, "age": 3, "carriedWeight": 55.,
                   "recentRaces": [{"date": "2026-07-01", "finish": n,
                                    "distance": 1600, "track": "東京",
                                    "surface": "芝", "fieldSize": 10}]}
                  for n in range(1, 5)
              ]}
    t = datetime.fromisoformat(day+"T11:00:00").replace(tzinfo=JST)
    return capture_preoff_features(detail, [1, 2, 3, 4], now=t)


def final(receipt):
    return {"raceId":receipt["raceId"], "status":"確定",
            "confirmedAtEpoch":receipt["postAtEpoch"] + 600,
            "finishers":[{"horseNumber":n, "finish":n} for n in (1,2,3,4)]}


def test_immutable_preoff_facts_join_only_to_confirmed_final_results(tmp_path):
    with open_store(tmp_path / "holds.sqlite") as connection:
        snap, receipt = sample("2026-08-01")
        append_capture(connection, snap, receipt, clock=receipt["capturedAtEpoch"] + 1)
        races, audit = build_verified_races(connection, [final(receipt)])
        assert len(races) == 1
        assert races[0]["horses"][0]["finish"] == 1
        assert races[0]["capturedAtEpoch"] < races[0]["postAtEpoch"]
        assert audit["verified_labelled_races"] == 1
        report = evaluate_verified_circuits(connection, [final(receipt)])
        assert report["byCircuitAndFamily"]["中央/flat"]["eligible"] is False
        assert report["claim80PercentAchieved"] is False


def test_invalid_and_missing_results_never_count_as_backtest_success(tmp_path):
    with open_store(tmp_path / "holds.sqlite") as connection:
        s1,r1=sample("2026-08-01")
        s2,r2=sample("2026-08-02", "地方")
        append_capture(connection,s1,r1,clock=r1["capturedAtEpoch"])
        append_capture(connection,s2,r2,clock=r2["capturedAtEpoch"])
        bad=final(r1)
        bad["confirmedAtEpoch"]=r1["postAtEpoch"]-20
        rows,audit=build_verified_races(connection,[bad])
        assert not rows
        assert audit["invalid_or_inconsistent_snapshot_or_result"]==1
        assert audit["no_independent_final_result"]==1
        assert audit["verified_labelled_races"]==0


@pytest.mark.parametrize("mutate",[
    lambda r: r.update(status="速報"),
    lambda r: r["finishers"].pop(),
    lambda r: r["finishers"][1].update(finish=1),
    lambda r: r["finishers"][1].update(horseNumber=1),
    lambda r: r.update(confirmedAtEpoch=None),
])
def test_invalid_labels_rejected_before_join(mutate):
    _,receipt=sample("2026-08-03")
    item=final(receipt)
    mutate(item)
    with pytest.raises(ValueError):
        _validated_results([item])


def test_duplicates_in_independent_result_file_are_fatal():
    _,r=sample("2026-08-04")
    with pytest.raises(ValueError, match="duplicate"):
        _validated_results([final(r),final(r)])
