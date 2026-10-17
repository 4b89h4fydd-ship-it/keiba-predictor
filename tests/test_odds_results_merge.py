"""Odds and official result merger separation contract."""
from arvexq.ingest.odds_results_merge import _merge_central_odds, _merge_result_fields

def test_live_odds_update_existing_runner():
    race={"horses":[{"horseNumber":1,"name":"A"},{"horseNumber":2,"name":"B"}]}
    out=_merge_central_odds(race,{1:{"winOdds":3.5,"popularity":1}})
    assert out["horses"][0]["winOdds"]==3.5
    assert "winOdds" not in out["horses"][1]
    assert out["oddsSource"]=="netkeiba実オッズ"

def test_results_add_missing_finishers_without_deleting_existing_horses():
    race={"horses":[{"horseNumber":1,"name":"A"}]}
    result={"finishers":[{"horseNumber":2,"name":"B","winOdds":8.3}]}
    out=_merge_result_fields(race,result)
    assert len(out["horses"])==2
    assert out["horses"][1]["name"]=="B"
    assert out["oddsType"]=="単勝最終オッズ"
