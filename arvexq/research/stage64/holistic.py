"""Evidence-only holistic horse comparison on the existing Stage64 path.

No new prediction route, odds feed, handicapping coefficients or inferred
course geometry. A winning claim must be supported by the pre-race observed
past starts; missing observations remain None rather than zero.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, date
from math import isfinite
from urllib.parse import urlsplit

from arvexq.research.stage63.ability import quality
from .circuits import discipline

OFFICIAL_COURSE_HOSTS = frozenset({
    "jra.go.jp", "www.jra.go.jp", "jra.jp", "www.jra.jp",
    "keiba.go.jp", "www.keiba.go.jp", "www.sonoda-himeji.jp",
    "www.nagoyakeiba.com", "www.keiba.or.jp", "www.sagakeiba.net",
    "www.kawasaki-keiba.jp", "www.tokyocitykeiba.com"
})


def _number(value):
    if type(value) not in (int, float):
        return None
    return float(value) if isfinite(value) else None


def _corner_positions(row):
    values = row.get("cornerPositions") or row.get("passing")
    n = row.get("fieldSize")
    if not isinstance(values, list) or not values or type(n) is not int or n < 3:
        return None
    if not all(type(x) in (int, float) and isfinite(x) and 1 <= x <= n
               for x in values):
        return None
    return values


def _previous_match_id(run):
    """Only link starters when actual prior race ID or full meeting identity exists."""
    date = str(run.get("_raceDate") or run.get("date") or "")
    track = str(run.get("track") or "").strip()
    no = run.get("raceNumber")
    if len(date) != 10 or not track or type(no) is not int or no < 1:
        return None
    return (date, track, no)


def _verified_first_corner(race):
    """Accept existing official source evidence, never infer from a course name."""
    record = race.get("courseGeometry")
    if not isinstance(record, dict) or record.get("sourceKind") != "official_course_geometry":
        return None
    uri = str(record.get("sourceUrl") or "")
    parsed = urlsplit(uri)
    meters = _number(record.get("firstCornerDistanceMeters"))
    published_text = record.get("publishedAt")
    try:
        published = datetime.fromisoformat(str(published_text).replace("Z", "+00:00"))
        race_day = date.fromisoformat(str(race["date"]))
        start = str(race.get("scheduledStartTime") or race.get("startTime") or "")
        from zoneinfo import ZoneInfo
        if published.tzinfo is None:
            return None
        published_jst = published.astimezone(ZoneInfo("Asia/Tokyo"))
        if published_jst.date() > race_day:
            return None
        # If an exact off-clock is unavailable, same-day information cannot
        # be certified pre-off. Never treat a UTC date as JST race date.
        if published_jst.date() == race_day:
            if len(start) < 5:
                return None
            off = datetime.fromisoformat(race["date"]+"T"+start[:5]).replace(
                tzinfo=ZoneInfo("Asia/Tokyo"))
            if published_jst >= off:
                return None
    except (ValueError, TypeError, KeyError):
        return None
    if (parsed.scheme != "https" or parsed.hostname not in OFFICIAL_COURSE_HOSTS
            or meters is None or meters <= 0 or meters >= 5000
            or str(record.get("track") or "") != str(race.get("track") or "")
            or _number(record.get("distance")) != _number(race.get("distance"))
            or str(record.get("surface") or "") != str(race.get("surface") or "")
            or not record.get("sourcePublishedBeforeOff", False)):
        return None
    return {"meters": meters, "sourceUrl": uri, "sourceKind": "official_course_geometry"}


def evidence(race, histories, active):
    """Full race-relative comparison; only historical observations enter."""
    by_number = {h["horseNumber"]: h for h in active}
    head_to_head = defaultdict(lambda: defaultdict(lambda: {"wins": 0, "losses": 0, "ties": 0,
                                                              "raceIds": []}))
    meetings = defaultdict(dict)
    facts = {}
    for no, rows in sorted(histories.items()):
        context = []
        for run in rows:
            if quality(run) is None or discipline(run) != discipline(race):
                continue
            mid = _previous_match_id(run)
            if mid is not None:
                meetings[mid][no] = run
            context.append(run)
        margins = []
        opposing = []
        gate = []
        sprint = []
        head = []
        for run in context:
            # Only seconds behind the winner; never silently mix lengths.
            raw_margin = next((_number(run.get(key)) for key in
                               ("marginSeconds", "timeBehindWinner")
                               if _number(run.get(key)) is not None), None)
            if raw_margin is not None and raw_margin >= 0:
                margins.append(raw_margin)
            lvl = _number(run.get("opponentLevel"))
            if lvl is not None and 0 <= lvl <= 1:
                opposing.append(lvl)
            timing = run.get("earlyTiming")
            if (isinstance(timing, dict)
                    and timing.get("sourceKind") == "individual_sensor"
                    and str(timing.get("sourceRef") or "").strip()):
                reaction = _number(timing.get("gateReactionSeconds"))
                first200 = _number(timing.get("first200mSeconds"))
                if reaction is not None and 0 <= reaction <= 10:
                    gate.append(reaction)
                if first200 is not None and 0 < first200 <= 60:
                    sprint.append(first200)
            positions = _corner_positions(run)
            if positions is not None:
                head.append(int(positions[0]))
        horse = by_number[no]
        comparable = [
            run for run in context
            if str(run.get("track") or "") == str(race.get("track") or "")
            and _number(run.get("distance")) is not None
            and _number(run.get("distance")) == _number(race.get("distance"))
            and (not race.get("surface") or run.get("surface") == race.get("surface"))
        ]
        # The sample count is explicitly recorded; a missing value is not bad.
        # Margin seconds are comparable only under observed matching course
        # and distance. A cross-course raw-margin mean would be a false input.
        comparable_margins = [
            value for row in comparable
            for value in [next((_number(row.get(key)) for key in
                               ("marginSeconds", "timeBehindWinner")
                               if _number(row.get(key)) is not None), None)]
            if value is not None and value >= 0
        ]
        comparable_margins.sort()
        facts[no] = {
            "historicalStarts": len(context),
            "historicalMarginSeconds": sorted(margins)[len(margins)//2] if margins else None,
            "historicalMarginSamples": len(margins),
            "sameTrackDistanceMarginSeconds": comparable_margins[len(comparable_margins)//2] if comparable_margins else None,
            "sameTrackDistanceMarginSamples": len(comparable_margins),
            "opponentLevelMedian": sorted(opposing)[len(opposing)//2] if opposing else None,
            "opponentLevelSamples": len(opposing),
            "individualGateReactionMedian": sorted(gate)[len(gate)//2] if gate else None,
            "individualGateReactionSamples": len(gate),
            "individualFirst200mMedian": sorted(sprint)[len(sprint)//2] if sprint else None,
            "individualFirst200mSamples": len(sprint),
            "observedFirstCornerSamples": len(head),
            "sameTrackDistanceStarts": len(comparable),
            "sameTrackDistanceWins": sum(row.get("finish") == 1 for row in comparable),
            "sameTrackDistanceTop3": sum(row.get("finish") <= 3 for row in comparable),
            "draw": horse.get("horseNumber"), "frame": horse.get("frameNumber"),
            "previousClassNames": sorted({str(row.get("class") or row.get("className"))
                                          for row in context
                                          if row.get("class") or row.get("className")}),
        }
    for mid, starters in meetings.items():
        # A recorded shared start establishes relative opposition directly.
        for a, a_run in starters.items():
            for b, b_run in starters.items():
                if a == b:
                    continue
                relation = head_to_head[a][b]
                if a_run["finish"] < b_run["finish"]:
                    relation["wins"] += 1
                elif a_run["finish"] > b_run["finish"]:
                    relation["losses"] += 1
                else:
                    relation["ties"] += 1
                relation["raceIds"].append("%s-%s-%s" % mid)
    # A historical race carries no guarantee the same conditions repeat today.
    return {"source": "preoff-recorded-history-no-outcome-or-odds",
            "byHorse": facts,
            "headToHead": {a: dict(v) for a, v in head_to_head.items()},
            "firstCorner": _verified_first_corner(race),
            "courseGeometryUnknown": _verified_first_corner(race) is None,
            "unknownDoesNotMeanAdverse": True, "winDecisionCalibrated": False}


def direct_rematch_candidate(order, observations):
    """A cautious research-only winner comparison, never guessed point weights.

    A direct shared-race rematch is necessary, but not sufficient: all
    *available comparable* margins, opponent strength, course records and
    individual start timing are checked for contradictions. Missing evidence
    cannot be silently treated as a win. Official geometry is a context
    observation, never a made-up inner-draw bonus.
    """
    if not order:
        return None
    leader = order[0]
    matches = observations["headToHead"]
    facts = observations["byHorse"]
    eligible = []
    for challenger in order[1:5]:
        record = matches.get(challenger, {}).get(leader, {})
        if (record.get("wins", 0) < 1 or record.get("losses", 0) != 0
                or record.get("ties", 0) != 0):
            continue
        a, b = facts[challenger], facts[leader]
        checks, unknown, corroborated = [], [], []
        contradictory = False
        # All margin observations compared here must have the same recorded
        # track and distance; unknown margin is not a 0-second performance.
        for label, key, prefer_lower, count_key in (
            ("same-track-distance-margin", "sameTrackDistanceMarginSeconds",
             True, "sameTrackDistanceMarginSamples"),
            ("observed-opponent-level", "opponentLevelMedian",
             False, "opponentLevelSamples"),
            ("same-track-distance-podium-record", "sameTrackDistanceTop3",
             False, "sameTrackDistanceStarts"),
        ):
            av, bv = a.get(key), b.get(key)
            if av is None or bv is None or not a.get(count_key) or not b.get(count_key):
                unknown.append(label)
                continue
            # Convert historical top-three COUNT into a per-start observation
            # rather than mistaking more starts for higher performance.
            if key == "sameTrackDistanceTop3":
                av = av / a[count_key]
                bv = bv / b[count_key]
            if (av > bv if prefer_lower else av < bv):
                contradictory = True
            elif (av < bv if prefer_lower else av > bv):
                corroborated.append(label)
            checks.append(label)
        # Only compare gate timing within an independently documented course
        # geometry. Different start courses do not have a common scale.
        if observations.get("firstCorner") is not None:
            key = "individualGateReactionMedian"
            if (a.get("individualGateReactionSamples") and
                    b.get("individualGateReactionSamples")):
                checks.append("individual-gate-reaction")
                if a[key] > b[key]:
                    contradictory = True
                elif a[key] < b[key]:
                    corroborated.append("individual-gate-reaction")
            else:
                unknown.append("individual-gate-reaction")
            checks.append("verified-first-corner-geometry")
        else:
            unknown.extend(["individual-gate-reaction", "verified-first-corner-geometry"])
        if not contradictory and corroborated:
            eligible.append((challenger, record["wins"], checks, unknown, corroborated))
    if len(eligible) != 1:
        return None
    challenger, count, checked, unknown, corroborated = eligible[0]
    return {"horseNumber": challenger, "otherHorseNumber": leader,
            "sharedPastRacesWon": count, "confirmedChecks": checked,
            "corroboratingEvidence": corroborated, "unavailableChecks": unknown,
            "reason": "head-to-head-precedence-corroborated-by-comparable-history",
            "researchOnly": True}
