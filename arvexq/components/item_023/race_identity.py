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
    except (TypeError,ValueError,OverflowError):return None
    if str(race_number).strip() not in (str(n),f"{n:02d}"):return None
    if not 1<=n<=12:return None
    return f"{c}-{parsed.isoformat()}-{venue}-{n:02d}"

def same_race(left,right):
    if not isinstance(left,dict) or not isinstance(right,dict):return False
    ids=[canonical_race_id(x.get("circuit"),x.get("date"),x.get("track"),x.get("raceNumber")) for x in (left,right)]
    return ids[0] is not None and ids[0]==ids[1]


def observed_detail_identity_error(detail):
    """Report observed envelope mismatch without guessing or changing stored data.

    Returns None for incomplete identity because absent facts are not contradictions.
    A canonical identity is checked only when all factual components are present.
    """
    if not isinstance(detail, dict):
        return None
    required = ("id", "circuit", "date", "track", "raceNumber")
    if any(detail.get(field) in (None, "") for field in required):
        return None
    expected = canonical_race_id(detail["circuit"], detail["date"],
                                 detail["track"], detail["raceNumber"])
    if expected is None or expected == str(detail["id"]):
        return None
    return {"raceId": detail["id"], "expectedRaceId": expected,
            "error": "race detail identity mismatch"}
