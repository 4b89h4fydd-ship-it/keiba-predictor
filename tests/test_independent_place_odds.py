"""Factual-only place odds, no UI or forecast changes."""
from arvexq.ingest.place_odds import place_odds,place_odds_pair

def test_invalid_missing_place_odds_never_assumed():
    for value in ('',None,'取消','---','0','1.8-1.2'):
        assert place_odds(value) is None
    assert place_odds('1.2～2.4')=={'placeOddsLow':1.2,'placeOddsHigh':2.4}
    assert place_odds_pair('1.2','2.4')=={'placeOddsLow':1.2,'placeOddsHigh':2.4}
    assert place_odds_pair('2.4','1.2') is None

def test_real_nar_parser_keeps_observed_place_columns_distinct():
    from app import _parse_nar_live_odds_html
    html='<table><tr><td>1</td><td>2</td><td>試験馬</td><td>3.2</td><td>1.2</td><td>2.1</td><td>牡3</td></tr></table>'
    result=_parse_nar_live_odds_html(html)
    assert result[2]['winOdds']==3.2
    assert result[2]['placeOddsLow']==1.2
    assert result[2]['placeOddsHigh']==2.1
