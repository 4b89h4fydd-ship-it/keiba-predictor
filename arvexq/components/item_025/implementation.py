"""Owned definitions, installed in the original app context by components.runtime.

The migration bridge preserves existing global state, decorators and monkeypatch
contracts. These definitions are not independently initialized modules yet.
"""

def _netkeiba_card_rows_fast(detail:dict)->list[dict]:
    rid=str(detail.get("netkeibaRaceId") or "") or _netkeiba_race_id(
        str(detail.get("date") or ""),str(detail.get("track") or ""),int(detail.get("raceNumber") or 0)
    )
    if not rid:return []
    try:
        html=_netkeiba_get(
            f"https://race.netkeiba.com/race/shutuba.html?race_id={rid}",
            float(os.getenv("FAST_CARD_TIMEOUT_SEC","1.2")),20
        )
    except Exception:return []
    soup=BeautifulSoup(html,"html.parser");rows=[]
    for tr in soup.select("tr.HorseList"):
        horse=_nk_row_horse(tr)
        if not horse:continue
        horse["source"]="netkeiba高速出走表"
        rows.append(horse)
    return rows
