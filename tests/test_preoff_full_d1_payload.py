"""Real D1 compressed snapshot regression for the pre-race sealer."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import pytest
from arvexq.ingest.full_snapshot_codec import pack_detail, KEY
from scripts.arvexq_freeze_predictions import detail_from, _history_count, fetch_existing_d1_detail

JST=timezone(timedelta(hours=9))
RID="jra-2026-11-18-京都-11"
NOW=datetime(2026,11,18,15,0,tzinfo=JST)


def full():
    return {"id":RID,"date":"2026-11-18","startTime":"15:40",
            "preRacePrediction":{"sealRevision":"unchanged-seal"},
            "horses":[{"horseNumber":i,"name":f"runner{i}",
                       "recentRaces":[{"date":"2026-10-21","finish":2,"distance":2000}],
                       "allPastRuns":[{"date":"2026-10-21","finish":2,"distance":2000}]}
                      for i in range(1,5)]}


def test_unpacks_history_and_existing_forecast_from_full_d1_envelope():
    raw=full()
    packed=pack_detail(raw)
    assert KEY in packed
    assert all(not h.get("recentRaces") for h in packed["horses"])
    restored=detail_from({"detail":packed},RID)
    assert restored==raw
    assert _history_count(restored)==4
    assert restored["preRacePrediction"]==raw["preRacePrediction"]


def test_primary_full_envelope_does_not_unnecessarily_consult_display():
    packed=pack_detail(full())
    requested=[]
    def reader(url):
        requested.append(url)
        return {"detail":packed}
    actual=fetch_existing_d1_detail("https://example.invalid",RID,now=NOW,reader=reader)
    assert _history_count(actual)==4
    assert len(requested)==1


def test_corrupt_archive_never_silently_falls_back_to_thin_index():
    packed=pack_detail(full())
    packed[KEY]["sha256"]="f"*64
    with pytest.raises(ValueError,match="restore mismatch"):
        detail_from({"detail":packed},RID)


def test_cross_race_embedded_archive_rejected():
    original=full()
    forged=pack_detail(original)
    other=deepcopy(original)
    other["id"]="jra-2026-11-18-京都-12"
    forged[KEY]=pack_detail(other)[KEY]
    with pytest.raises(ValueError,match="identity mismatch"):
        detail_from({"detail":forged},RID)


def test_nonpacked_plain_detail_backward_compatible():
    raw=full()
    assert detail_from({"race":raw},RID) is raw
    assert detail_from({"race":raw},"not-this-race") is None
