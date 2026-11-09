"""Factual-only place odds, no UI or forecast changes."""
from arvexq.ingest.place_odds import place_odds,place_odds_pair

def test_invalid_missing_place_odds_never_assumed():
    for value in ('',None,'取消','---','0','1.8-1.2'):
        assert place_odds(value) is None
    assert place_odds('1.2～2.4')=={'placeOddsLow':1.2,'placeOddsHigh':2.4}
    assert place_odds_pair('1.2','2.4')=={'placeOddsLow':1.2,'placeOddsHigh':2.4}
    assert place_odds_pair('2.4','1.2') is None

def test_pair_with_separator_travelling_in_low_cell():
    # Live keiba.go.jp layout (2026-11-04 Sonoda 4R): the range is split
    # across two cells and the separator stays in the low cell.
    assert place_odds_pair('3.5-','7.8')=={'placeOddsLow':3.5,'placeOddsHigh':7.8}
    assert place_odds_pair('1.1-','2.1')=={'placeOddsLow':1.1,'placeOddsHigh':2.1}
    # Pre-sales zeros are still never treated as observed odds.
    assert place_odds_pair('0.0-','0.0') is None
    assert place_odds_pair('','') is None
    # The single-value contract is unchanged: a dangling separator alone
    # is an incomplete value, not a point estimate.
    assert place_odds('3.5-') is None

def test_real_nar_parser_keeps_observed_place_columns_distinct():
    from app import _parse_nar_live_odds_html
    html='<table><tr><td>1</td><td>2</td><td>試験馬</td><td>3.2</td><td>1.2</td><td>2.1</td><td>牡3</td></tr></table>'
    result=_parse_nar_live_odds_html(html)
    assert result[2]['winOdds']==3.2
    assert result[2]['placeOddsLow']==1.2
    assert result[2]['placeOddsHigh']==2.1
