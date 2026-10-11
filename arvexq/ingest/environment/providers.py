"""environment/providers: acquisition behavior preserved from PR #13 (95f2595).

Keyword-only ports are supplied by the application composition root.
This module never imports app or initializes storage/background workers.
"""
import time
import urllib.parse
import urllib.request


from arvexq.ingest.local.state import NAR_BABA_CODES

def _nar_fetch_environment(track: str, iso_date: str, race_no: int, *, _environment_http_get, _parse_nar_environment_html, _today_iso) -> dict:
    code=NAR_BABA_CODES.get(str(track or "").strip())
    if not code or not race_no:return {}
    q=urllib.parse.urlencode({"k_babaCode":code,"k_raceDate":iso_date.replace("-","/"),"k_raceNo":int(race_no)})
    urls=[
        "https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/DebaTableSmall?"+q,
        "https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/RaceMarkTable?"+q,
    ]
    out={}
    for url in urls:
        try:parsed=_parse_nar_environment_html(_environment_http_get(url,25 if iso_date==_today_iso() else 86400))
        except Exception as exc:
            print("NAR environment fetch failed",track,iso_date,race_no,exc);continue
        for k in ("weather","condition"):
            if parsed.get(k) not in (None,"","不明"):out[k]=parsed[k]
        if parsed.get("scratchMap"):out["scratchMap"]=parsed["scratchMap"]
        if out.get("weather") and out.get("condition") and "scratchMap" in out:break
    if out:
        out.update({"source":"NAR公式","updatedAtEpoch":int(time.time()),"raceNo":int(race_no)})
    return out


def _jra_fetch_environment(row: dict, *, _env_clean_condition, _env_clean_weather, _jra_find_cname, _jra_request, _netkeiba_race_meta, _parse_jra_environment_html, _today_iso) -> dict:
    date=str(row.get("date") or "")
    track=str(row.get("track") or "")
    race_no=int(row.get("raceNumber") or 0)
    surface=str(row.get("surface") or "")
    cname=str(row.get("jraCname") or "")
    if not cname:
        try:cname=_jra_find_cname(date,track,race_no)
        except Exception:cname=""
    out={}
    if cname:
        try:
            html=_jra_request("https://www.jra.go.jp/JRADB/accessD.html",cname,20 if date==_today_iso() else 86400)
            out=_parse_jra_environment_html(html,surface)
        except Exception as exc:
            print("JRA environment official failed",date,track,race_no,exc)
    # Secondary source only fills a field the official page did not provide.
    if out.get("weather") in (None,"","不明") or out.get("condition") in (None,"","不明"):
        try:
            meta=_netkeiba_race_meta(row)
            if out.get("weather") in (None,"","不明") and meta.get("weather") not in (None,"","不明"):
                out["weather"]=_env_clean_weather(meta.get("weather"))
            if out.get("condition") in (None,"","不明") and meta.get("condition") not in (None,"","不明"):
                out["condition"]=_env_clean_condition(meta.get("condition"))
        except Exception as exc:
            print("JRA environment secondary failed",date,track,race_no,exc)
    if out.get("weather") not in (None,"","不明") or out.get("condition") not in (None,"","不明"):
        out.update({"source":"JRA公式優先","updatedAtEpoch":int(time.time())})
    return out
