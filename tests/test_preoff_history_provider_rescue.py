"""Bounded, evidence-only pre-off career rescue regression tests."""
import json
from copy import deepcopy
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace

import pytest
from scripts.arvexq_preoff_history_rescue import accept_observed_rescue
from scripts.arvexq_freeze_predictions import recover_prior_history_before_post

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


def test_sealer_orchestrates_isolated_bounded_offline_provider():
    calls=[]
    def runner(args, **kwargs):
        calls.append((args,kwargs))
        assert kwargs["timeout"] == 55
        assert kwargs["capture_output"] is True
        assert "arvexq_preoff_history_rescue.py" in args[-1]
        return SimpleNamespace(returncode=0, stdout=json.dumps(enriched()),
                               stderr="")
    result=recover_prior_history_before_post(sample(),now=NOW,run=runner)
    assert len(calls)==1
    assert len(result["horses"][0]["allPastRuns"])==2


def test_sealer_fails_closed_if_provider_errors_or_returns_mismatched_field():
    def err(*a,**kwargs):
        return SimpleNamespace(returncode=1,stderr="no provider facts",stdout="")
    with pytest.raises(RuntimeError,match="no verified"):
        recover_prior_history_before_post(sample(),now=NOW,run=err)
    wrong=enriched()
    wrong["horses"][0]["name"]="somebody else"
    def mismatch(*a,**kwargs):
        return SimpleNamespace(returncode=0,stdout=json.dumps(wrong),stderr="")
    with pytest.raises(ValueError,match="active field mismatch"):
        recover_prior_history_before_post(sample(),now=NOW,run=mismatch)


def test_never_invokes_provider_after_start():
    calls=[]
    with pytest.raises(ValueError,match="post-off"):
        recover_prior_history_before_post(
            sample(),now=datetime(2026,11,18,15,41,tzinfo=JST),
            run=lambda *a,**k:calls.append(True))
    assert not calls
