"""Pure, standalone parsing utilities.

Moved verbatim from app.py; the corresponding app-level names remain imported.
No external API, DB, or live racing access is performed at import time.
"""

def decode_csv_bytes(raw: bytes) -> str:
    for encoding in ("utf-8-sig", "cp932", "shift_jis", "utf-8"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _jra_decode(raw: bytes) -> str:
    for enc in ("utf-8","cp932","shift_jis"):
        try:
            return raw.decode(enc)
        except Exception:
            pass
    return raw.decode("utf-8","ignore")


def _decode_site(raw:bytes)->str:
    for enc in ("utf-8","euc_jp","cp932","shift_jis"):
        try:return raw.decode(enc)
        except Exception:pass
    return raw.decode("utf-8","ignore")


def _json_horse_rows(body)->list[dict]:
    if isinstance(body,list):return [x for x in body if isinstance(x,dict)]
    if not isinstance(body,dict):return []
    for k in ("horses","entries","rows","data","raceEntries","values"):
        z=body.get(k)
        if isinstance(z,list):return [x for x in z if isinstance(x,dict)]
        if isinstance(z,dict):
            for kk in ("horses","entries","rows","data"):
                zz=z.get(kk)
                if isinstance(zz,list):return [x for x in zz if isinstance(x,dict)]
    return []


def _pick(d,*keys):
    if not isinstance(d,dict):return None
    for k in keys:
        if k in d and d.get(k) not in (None,""):return d.get(k)
    return None


def _jra_run_key(r:dict)->tuple:
    """Stable horse-start key across JRA/profile/supplemental sources.

    A horse cannot run twice at the same track on the same date, so title wording
    must not prevent two representations of the same start from being merged.
    """
    date=str(r.get("date") or "");track=str(r.get("track") or "");distance=int(r.get("distance") or 0)
    if date:return (date,track,distance)
    return (date,track,distance,str(r.get("title") or ""),str(r.get("raceId") or ""))


def _jra_run_value_present(key:str,value)->bool:
    if value in (None,"",[],{},"不明"):return False
    if key in {"finish","fieldSize","distance","timeSeconds","last3FSeconds","last3FRank","last3FPercentile","carriedWeight","racePrize1","raceNumber"}:
        try:return float(value)>0
        except (TypeError,ValueError):return False
    return True
