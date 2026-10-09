"""Pre-off five-run comparison; explicitly separates observations from inference.

Date-bounded, deduplicated, and ordered before sampling. No post-off records,
no raw sectional-time comparison across distances, and no invented class score.
The output is evidence, not a calibrated podium probability.
"""
from __future__ import annotations
import re
from datetime import date, datetime
from typing import Any
from arvexq.history import normalize_run
from arvexq.ingest.full_career import merge_career

VERSION = "arvexq-past-five-context-v1"
KEYS = ("recentRaces", "allPastRuns", "pastRaces", "history", "runs")

def _date(x: Any) -> date | None:
    if isinstance(x, datetime):
        return x.date()
    if isinstance(x, date):
        return x
    text = str(x or "").strip().replace("/", "-").replace(".", "-")
    if re.fullmatch(r"\d{8}", text):
        text = text[:4] + "-" + text[4:6] + "-" + text[6:]
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None

def _number(x: Any) -> float | None:
    try:
        if x is None or x == "":
            return None
        val = float(x)
        return val if val == val and abs(val) != float("inf") else None
    except (ValueError, TypeError):
        return None

def _positions(x: Any) -> list[int]:
    if isinstance(x, list):
        vals = x
    else:
        vals = re.findall(r"\d+", str(x or ""))
    out: list[int] = []
    for n in vals:
        try:
            v = int(n)
            if v > 0:
                out.append(v)
        except (TypeError, ValueError):
            continue
    return out

def observed_runs(horse: dict[str, Any], race: dict[str, Any], limit: int | None = 5) -> list[dict[str, Any]]:
    cutoff = _date(race.get("date") or race.get("raceDate"))
    if cutoff is None:
        return []
    candidates: list[dict[str, Any]] = []
    for key in KEYS:
        if isinstance(horse.get(key), list):
            candidates.extend(horse[key])
    rows: list[dict[str, Any]] = []
    for original in merge_career([], candidates, cutoff.isoformat()):
        row = normalize_run(original)
        field = _number(row.get("fieldSize"))
        finish = _number(row.get("finish"))
        if field is None or field < 2 or finish is None or not (1 <= finish <= field):
            continue
        row.update({k: v for k, v in original.items() if k not in row})
        row["_raceDate"] = original["date"]
        row["finish"] = int(finish)
        row["fieldSize"] = int(field)
        rows.append(row)
    return rows if limit is None else rows[:max(0, int(limit))]

def analyze_past_performance(horse: dict[str, Any], race: dict[str, Any]) -> dict[str, Any]:
    runs = observed_runs(horse, race)
    distance = _number(race.get("distance") or race.get("distanceM"))
    track = str(race.get("track") or "").strip()
    surface = str(race.get("surface") or "").strip()
    going = str(race.get("condition") or race.get("going") or "").strip()
    entries: list[dict[str, Any]] = []
    observed_opponent_levels: list[float] = []
    observed_margins: list[float] = []
    for row in runs:
        field = int(row["fieldSize"])
        finish = int(row["finish"])
        dist = _number(row.get("distance"))
        same_distance = bool(distance and dist and abs(distance-dist) <= 150)
        same_track = bool(track and row.get("track") and str(row["track"]).strip() == track)
        same_surface = bool(surface and row.get("surface") and str(row["surface"]).strip() == surface)
        same_going = bool(going and (row.get("condition") or row.get("going"))
                          and str(row.get("condition") or row.get("going")).strip() == going)
        # Unknown surface cannot be treated as a match.
        comparable = same_distance and same_surface
        passage = _positions(row.get("cornerPositions") or row.get("passing"))
        first = passage[0] if passage else 0
        last = passage[-1] if passage else 0
        front = bool(first and first <= max(2, (field+2)//3))
        faded = bool(front and finish > max(3, (field*2)//3))
        level = _number(row.get("opponentLevel"))
        margin = _number(row.get("margin") or row.get("marginSeconds") or
                         row.get("beatenLength") or row.get("着差"))
        if level is not None:
            observed_opponent_levels.append(level)
        if margin is not None:
            observed_margins.append(margin)
        late_rank = _number(row.get("last3fRank") or row.get("last600Rank") or
                            row.get("上がり順位"))
        entries.append({
            "date": row["_raceDate"], "finish": finish, "fieldSize": field,
            "finishQuality": round((field-finish)/(field-1), 5),
            "top3": finish<=3, "sameDistance": same_distance,
            "sameTrack": same_track, "sameSurface": same_surface,
            "sameGoing": same_going, "comparable": comparable,
            "firstCorner": first or None, "lastCorner": last or None,
            "frontFaded": faded,
            "closingGain": (last-finish) if last else None,
            "last3fObserved": _number(row.get("last3f")) is not None,
            "opponentLevelObserved": level is not None,
            "opponentLevel": level,
            "marginObserved": margin is not None,
            "closingRank": int(late_rank) if late_rank is not None
                           and 1<=late_rank<=field else None,
        })
    count = len(entries)
    top3 = sum(x["top3"] for x in entries)
    weights = [5,4,3,2,1]
    form = (sum(weights[i]*e["finishQuality"] for i,e in enumerate(entries)) /
            sum(weights[:count])) if count else None
    comparable = [e for e in entries if e["comparable"]]
    comparable_podium = sum(x["top3"] for x in comparable)
    comparable_quality = sum(x["finishQuality"] for x in comparable)/len(comparable) if comparable else None
    fades = sum(x["frontFaded"] for x in entries)
    flags: list[str] = []
    if len(comparable)>=2 and comparable_podium==0:
        flags.append("same-surface-distance-no-podium")
    if fades >= 2:
        flags.append("repeated-front-fade")
    if len(entries)>=4 and sum(x["top3"] for x in entries[:2])==0 and sum(x["top3"] for x in entries[2:])>=2:
        flags.append("recent-form-downturn")
    return {
        "version": VERSION, "datedRuns": count, "top3": top3,
        "top3Rate": round(top3/count,5) if count else None,
        "recentFormQuality": round(form,5) if form is not None else None,
        "comparableRuns": len(comparable),
        "comparableTop3": comparable_podium,
        "comparableQuality": round(comparable_quality,5) if comparable_quality is not None else None,
        "trackMatchedRuns": sum(x["sameTrack"] for x in entries),
        "goingMatchedRuns": sum(x["sameGoing"] for x in entries),
        "last3fObservedRuns": sum(x["last3fObserved"] for x in entries),
        "opponentLevelObservedRuns": sum(x["opponentLevelObserved"] for x in entries),
        "frontFadeCount": fades, "riskFlags": flags, "runs": entries,
        "opponentLevelMean": (round(sum(observed_opponent_levels)/len(observed_opponent_levels),5)
                              if observed_opponent_levels else None),
        "marginMean": (round(sum(observed_margins)/len(observed_margins),5)
                       if observed_margins else None),
        "closingTop3Ranks": sum(e["closingRank"] is not None and e["closingRank"]<=3
                                 for e in entries),
        "marginObservedRuns": len(observed_margins),
        "status": "dated-observed" if count else "missing-dated-past-runs",
        "note": "Observed five-run context, not calibrated accuracy; no cross-distance raw 3F comparison.",
    }
