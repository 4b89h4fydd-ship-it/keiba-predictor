"""Contextual all-career evidence alongside strictly recent-five form."""
from __future__ import annotations
from statistics import mean, pstdev
from typing import Any
from arvexq.prediction.past_performance import observed_runs, _number

def profile_career(horse: dict[str, Any], race: dict[str, Any]) -> dict[str, Any]:
    rows = observed_runs(horse, race, limit=None)
    distance = _number(race.get("distance") or race.get("distanceM"))
    track = str(race.get("track") or "")
    surface = str(race.get("surface") or "")
    going = str(race.get("condition") or race.get("going") or "")
    qualities = []
    comparable = []
    grouped: dict[str, list[float]] = {k: [] for k in ("track","distance","surface","going")}
    representative = None
    class_seen = time_seen = margin_seen = sectional_seen = 0
    for row in rows:
        field, finish = int(row["fieldSize"]), int(row["finish"])
        quality = (field - finish) / (field - 1)
        qualities.append(quality)
        dist = _number(row.get("distance"))
        match_dist = bool(distance and dist and abs(distance - dist) <= 150)
        match_track = bool(track and row.get("track") and str(row["track"]) == track)
        match_surface = bool(surface and row.get("surface") and str(row["surface"]) == surface)
        match_going = bool(going and (row.get("condition") or row.get("going")) and
                           str(row.get("condition") or row.get("going")) == going)
        for name, matched in (("distance",match_dist),("track",match_track),
                              ("surface",match_surface),("going",match_going)):
            if matched:
                grouped[name].append(quality)
        if match_dist and match_surface:
            comparable.append((quality, finish <= 3))
            if representative is None or quality > representative["finishQuality"]:
                representative = {
                    "date": row["_raceDate"], "finish": finish, "fieldSize": field,
                    "finishQuality": round(quality, 5), "track": row.get("track"),
                    "surface": row.get("surface"), "distance": row.get("distance"),
                    "jockey": row.get("jockey"), "carriedWeight": row.get("carriedWeight"),
                    "class": row.get("class") or row.get("className"),
                }
        class_seen += bool(row.get("class") or row.get("className") or
                           _number(row.get("opponentLevel")) is not None)
        time_seen += bool(row.get("timeSeconds") or row.get("time"))
        margin_seen += bool(_number(row.get("margin") or row.get("marginSeconds")) is not None)
        sectional_seen += bool(_number(row.get("last3f")) is not None)
    recent = rows[:5]
    audit = horse.get("_careerHistoryAudit") if isinstance(horse.get("_careerHistoryAudit"),dict) else {}
    return {
        "version": "arvexq-observed-career-profile-v1",
        "datedRuns": len(rows), "recentRuns": len(recent),
        "top3": sum(row["finish"] <= 3 for row in rows),
        "top3Rate": round(sum(row["finish"] <= 3 for row in rows)/len(rows), 5) if rows else None,
        "recentTop3": sum(row["finish"] <= 3 for row in recent),
        "recentTop3Rate": round(sum(row["finish"] <= 3 for row in recent)/len(recent), 5) if recent else None,
        "peakFinishQuality": round(max(qualities),5) if qualities else None,
        "stability": round(max(0,1-pstdev(qualities)),5) if len(qualities)>1 else None,
        "comparableRuns": len(comparable),
        "comparableTop3": sum(top3 for _,top3 in comparable),
        "comparableQuality": round(mean(q for q,_ in comparable),5) if comparable else None,
        "sameTrackQuality": round(mean(grouped["track"]),5) if grouped["track"] else None,
        "sameDistanceQuality": round(mean(grouped["distance"]),5) if grouped["distance"] else None,
        "sameSurfaceQuality": round(mean(grouped["surface"]),5) if grouped["surface"] else None,
        "sameGoingQuality": round(mean(grouped["going"]),5) if grouped["going"] else None,
        "classObserved": class_seen, "timeObserved": time_seen,
        "marginObserved": margin_seen, "sectionalObserved": sectional_seen,
        "representativeComparable": representative,
        "unobservedMinimum": audit.get("unobservedMinimum"),
        "coverageStatus": audit.get("status","unverified"),
        "status": "observed-only" if rows else "missing-dated-career-history",
    }
