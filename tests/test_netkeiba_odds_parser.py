import json
from arvexq.ingest.netkeiba_odds_parser import _parse_netkeiba_win_odds_payload

def test_win_odds_json():
    raw=json.dumps({"data":{"odds":{"1":{"1":["3.5","",1],"2":["12.4","",5]}}}})
    assert _parse_netkeiba_win_odds_payload(raw)[1]["winOdds"] == 3.5
    assert _parse_netkeiba_win_odds_payload(raw)[2]["popularity"] == 5

def test_invalid_payload_is_empty():
    assert _parse_netkeiba_win_odds_payload("invalid") == {}
