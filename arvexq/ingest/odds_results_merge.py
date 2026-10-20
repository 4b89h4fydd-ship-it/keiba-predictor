"""Horse-level final results and live odds merges, with no application dependency."""
from datetime import datetime
from zoneinfo import ZoneInfo

def _merge_central_odds(detail:dict, odds:dict)->dict:
    if not odds:return detail
    by={int(h.get("horseNumber") or 0):h for h in detail.get("horses",[]) or []}
    for no,z in odds.items():
        h=by.get(int(no))
        if h:
            for k,v in z.items():
                if v not in (None,""):h[k]=v
    detail["oddsSource"]="netkeiba実オッズ";detail["oddsType"]="単勝実オッズ";detail["oddsUpdatedAt"]=datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%H:%M:%S")
    return detail

from arvexq.components.item_084.result_merge import _merge_result_fields
