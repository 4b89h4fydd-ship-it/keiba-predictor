"""Pre-off seal persists lossless compressed details without erasing rich D1 careers."""
from copy import deepcopy
import pytest

from arvexq.ingest.full_snapshot_codec import KEY, unpack_detail, pack_detail
from scripts.arvexq_freeze_predictions import encode_sealed_d1_sync_detail


def rich_detail():
    return {"id":"jra-2026-10-19-東京-11", "date":"2026-10-19",
            "startTime":"15:40", "preRacePrediction":{
                "sealRevision":"fixed-before-off","horses":[{"horseNumber":1,"mark":"◎"}]},
            "preRaceBet":{"items":[],"fixedBeforePost":True},
            "horses":[{"horseNumber":i,"name":f"runner{i}",
                       "allPastRuns":[{"date":f"2026-09-{j:02d}","finish":j%5+1,
                                       "track":"東京","distance":1600,
                                       "margin":0.2} for j in range(1,25)],
                       "recentRaces":[{"date":"2026-09-24","finish":2}]}
                      for i in range(1,19)]}


def test_rich_full_detail_is_losslessly_packed_for_worker():
    original=rich_detail()
    prior=deepcopy(original)
    packed=encode_sealed_d1_sync_detail(original)
    assert KEY in packed
    assert packed["id"]==original["id"]
    assert unpack_detail(packed)==original
    assert original==prior
    assert all("allPastRuns" not in h for h in packed["horses"])
    assert unpack_detail(packed)["preRacePrediction"]==original["preRacePrediction"]
    assert len(unpack_detail(packed)["horses"][0]["allPastRuns"])==24


def test_previously_packed_rows_can_be_restored_and_repacked_without_loss():
    original=rich_detail()
    already=pack_detail(original)
    assert encode_sealed_d1_sync_detail(unpack_detail(already))==already


def test_reject_overlarge_row_without_truncating_historical_observations():
    original=rich_detail()
    with pytest.raises(ValueError,match="safe D1 budget"):
        encode_sealed_d1_sync_detail(original,max_row_bytes=100)
    assert len(original["horses"][0]["allPastRuns"])==24


def test_no_identity_rejected():
    with pytest.raises(ValueError,match="identity"):
        encode_sealed_d1_sync_detail({"horses":[]})
