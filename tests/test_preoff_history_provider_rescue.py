"""Bounded, evidence-only pre-off career rescue regression tests."""
import json
from copy import deepcopy
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace

import pytest
from scripts.arvexq_preoff_history_rescue import accept_observed_rescue

JST = timezone(timedelta(hours=9))
NOW = datetime(2026, 11, 18, 15, 0, tzinfo=JST)


def sample():
    return {"id":"jra-2026-10-18-京都-11", "date":"2026-11-18",
            "startTime":"15:40", "horses":[
                {"horseNumber":no,"name":"horse"+str(no),"recentRaces":[]}
                for no in (1,2,3,4)]}


def enriched():
    candidate=sample()
    for h in candidate["horses"]:
        h["allPastRuns"]=[{"date":"2026-09-20","finish":2,"distance":2000},
                          {"date":"2026-08-10","finish":3,"distance":1800}]
    return candidate


def test_accepts_only_genuinely_prior_dated_provider_runs():
    original=sample()
    candidate=enriched()
    candidate["horses"][0]["allPastRuns"].extend([
        {"date":"2026-11-18","finish":1},
        {"date":"2026-11-19","finish":1},
        {"finish":1}])
    accepted=accept_observed_rescue(original,candidate,now=NOW)
    assert original==sample()
    assert len(accepted["horses"][0]["allPastRuns"])==2
    assert accepted["horses"][0]["recentRaces"][0]["date"]=="2026-09-20"
    assert "preRacePrediction" not in accepted


def test_roster_change_or_postoff_rejected():
    candidate=enriched()
    candidate["horses"][0]["name"]="different"
    with pytest.raises(ValueError,match="roster"):
        accept_observed_rescue(sample(),candidate,now=NOW)
    with pytest.raises(ValueError,match="post-off"):
        accept_observed_rescue(sample(),enriched(),
                               now=datetime(2026,11,18,15,41,tzinfo=JST))


def test_no_observed_history_never_becomes_fake_success():
    with pytest.raises(ValueError,match="no additional"):
        accept_observed_rescue(sample(),sample(),now=NOW)
