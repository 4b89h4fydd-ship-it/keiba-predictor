"""Sealed B holdout input rejects post-hoc labels, missing seals, bad races."""
from copy import deepcopy
from datetime import datetime,timedelta,timezone
import json

from arvexq.prediction.prerace_archive import JST, seal_detail
from arvexq.ingest.full_snapshot_codec import pack_detail
from scripts.arvexq_sealed_b_real_holdout import eligible,compare_files


def fixture(day,*,sealed=True,finish=True):
    dt=datetime.fromisoformat(day+"T11:00:00").replace(tzinfo=JST)
    race={"id":"jra-"+day+"-東京-01","date":day,"startTime":"12:00",
          "track":"東京","surface":"芝","distance":1600,"circuit":"中央",
          "horses":[{"horseNumber":n,"name":f"馬{n}","age":3,
                     "recentRaces":[{"date":"2026-07-01","track":"東京",
                                     "surface":"芝","distance":1600,
                                     "finish":n,"fieldSize":8,
                                     "cornerPositions":[n,n,n,n]}]}
                    for n in range(1,5)]}
    if sealed:
        marks={"raceId":race["id"],"raceDate":day,
               "capturedAtEpoch":int(dt.timestamp()),"markCount":3,
               "horses":[{"horseNumber":n,"mark":m} for n,m in
                         ((1,"◎"),(2,"○"),(3,"▲"))]}
        race=seal_detail(race,marks,dt)
    if finish:
        race["result"]={"status":"確定",
                        "finishers":[{"horseNumber":n,"finish":n} for n in range(1,5)]}
    return race


def test_verified_seal_and_confirmed_finish_required():
    d=fixture("2026-08-01")
    case,reason=eligible(d)
    assert case is not None and not reason
    assert case["result"]["finishers"][0]["horseNumber"]==1
    assert eligible(fixture("2026-08-01",sealed=False))[0] is None
    assert eligible(fixture("2026-08-01",finish=False))[0] is None


def test_rejects_incomplete_label_field_or_dead_heat():
    d=fixture("2026-08-02")
    d["result"]["finishers"][1]["finish"]=1
    assert eligible(d)[0] is None
    d=fixture("2026-08-02")
    d["result"]["finishers"].pop()
    assert eligible(d)[0] is None


def test_compressed_sealed_source_validated_and_insufficient_reported(tmp_path):
    d=fixture("2026-08-03")
    assert eligible(pack_detail(d))[0] is not None
    (tmp_path/"day.json").write_text(json.dumps({"details":[pack_detail(d)]},ensure_ascii=False))
    rep=compare_files([tmp_path/"day.json"],min_train=10,min_test=2)
    assert rep["eligibleSealedRaces"]==1
    assert rep["productionEligible"] is False
    assert rep["claim80PercentAchieved"] is False
    assert rep["byCircuitAndFamily"]["中央/flat"]["status"]=="insufficient-independent-chronological-sample"


def test_duplicate_race_id_fatal(tmp_path):
    d=fixture("2026-08-04")
    (tmp_path/"data.json").write_text(json.dumps({"details":[d,d]},ensure_ascii=False))
    try:
        compare_files([tmp_path/"data.json"])
        assert False,"duplicate must be rejected"
    except ValueError as e:
        assert "duplicate" in str(e)
