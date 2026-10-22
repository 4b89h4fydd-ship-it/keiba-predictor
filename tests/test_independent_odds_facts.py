"""Factual-only odds evidence guards and production wiring."""
from stage4_source_support import implementation_source
from pathlib import Path
import math
from arvexq.ingest.odds_fields.missing import odds_missing,valid_win_odds
from arvexq.ingest.odds_fields.delta import win_odds_delta

def test_unknown_odds_are_not_numeric_zero_evidence():
    for value in (None, "", "取消", 0, -2, float("nan"), float("inf"), True):
        assert not valid_win_odds(value)
        assert odds_missing({"winOdds":value})
        assert win_odds_delta(value,3.2) is None
    assert odds_missing({})
    assert valid_win_odds("3.2")

def test_market_delta_requires_two_observed_prices():
    assert win_odds_delta(3.2,2.7)==-0.5
    assert win_odds_delta(2.7,3.2)==0.5
    assert win_odds_delta(3.2,3.2)==0.0
    assert win_odds_delta(None,None) is None

def test_live_nar_uses_delta_and_restore_checks_missing():
    source=implementation_source()
    live=source.split("def _attach_nar_live_odds(",1)[1].split("\ndef ",1)[0]
    restore=source.split("def _restore_saved_odds(",1)[1].split("\ndef ",1)[0]
    assert 'win_odds_delta(h.get("winOdds"),z.get("winOdds"))' in live
    assert 'if delta is not None: h["observedWinOddsDelta"]=delta' in live
    assert 'if not odds_missing(h)' in restore
