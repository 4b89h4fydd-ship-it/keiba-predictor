"""Independent item #23: canonical race ID comparison from factual identity.

Does not infer a race when date, venue or race number is unavailable.
"""
import re
from datetime import date

def canonical_race_id(circuit, race_date, track, race_number):
    c=str(circuit or "").strip().lower()
    if c in ("中央","jra"):c="jra"
    elif c in ("地方","nar"):c="nar"
    else:return None
    d=str(race_date or "").strip().replace("/", "-")
    try:
        parsed=date.fromisoformat(d)
    except ValueError:return None
    venue=str(track or "").strip()
    if not venue or not re.fullmatch(r"[\w一-龥々ヶー・]+",venue):return None
    try:n=int(race_number)
    except (TypeError,ValueError):return None
    if str(race_number).strip() not in (str(n),f"{n:02d}"):return None
    if not 1<=n<=12:return None
    return f"{c}-{parsed.isoformat()}-{venue}-{n:02d}"

def same_race(left,right):
    if not isinstance(left,dict) or not isinstance(right,dict):return False
    ids=[canonical_race_id(x.get("circuit"),x.get("date"),x.get("track"),x.get("raceNumber")) for x in (left,right)]
    return ids[0] is not None and ids[0]==ids[1]
