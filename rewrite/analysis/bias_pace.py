"""Same-day track bias, read from today's finished races and overlaid
on the netkeiba AI pace forecast (展開予想).

User instruction (2026-11-19): 「バイアスを読んでネット競馬の展開予想に
あわせてだせばええやん」 — read the day's bias and issue the pace
forecast adjusted by it.

The bias DEFINITION is fixed by the 2026-11-16 validation
(hidden_files/track-bias-20261116/REPORT.md) and is not changed here:

- Source races are only races on the same date at the same track
  that finished BEFORE the target race (no leakage). A source race
  qualifies when at least 80% of its finishers carry a first-corner
  position (the validation's main-analysis coverage gate).
- Front/back bias FB: with q = corner1 / field size, the top-3 rate
  of the front group (q <= 1/3) minus the top-3 rate of the closer
  group (q > 2/3), pooled across source races. Positive FB means
  the front is holding up today (前残り).
- Inside/outside bias IO: with r = horse number / field size, the
  top-3 rate of the inner group (r <= 1/3) minus the top-3 rate of
  the outer group (r > 2/3), pooled the same way. Positive IO means
  the inside is advantaged today.
- Shrinkage: the reported bias is the raw difference times
  w = S / (S + 2), S = the number of source races used. With no
  source races the bias is exactly 0 (neutral) — nothing is ever
  estimated or filled in.

The overlay expresses each horse's exposure to that bias through
the netkeiba pace forecast itself (the horse's forecast position,
not a past-run style profile):

    frontness(h)  = (0.5 - mean forecast pct(h)) * 2   in [-1, 1]
    frame(h)      = +1 inner / 0 middle / -1 outer     (number ratio)
    adjustment(h) = FB * frontness(h) + IO * frame(h)

The adjustment is a unit-free logit-style addend on the same scale
as the 2026-11-16 validation's overlay (which applied its own
fitted coefficients a, b on top). Any scaling coefficient belongs
to the caller and to a future validation; this module deliberately
carries none.

Inputs are plain dicts in the shapes the production data already
uses:

- day races / target race: {"date", "track", "raceNo", "startTime",
  "finishers": [{"horseNumber", "finish", "cornerPositions"}]}
  where cornerPositions[0] is the first-corner position (the field
  the result parser is being extended to fill; until it lands in
  production data every race simply reads as no-bias).
- pace forecast: either one race's pace-forecast.json entry
  ({"pace": label, "positions": {phase: [[numbers...], ...]}}) via
  pace_positions_from_forecast, or the materials per-horse form
  {number: {phase: {"rank", "pct"}}} that nk_materials consumes.

This module is NOT wired into the publish lane or the UI yet. It
changes no production probability, mark or display; it exists so
the connection is a small step once cornerPositions reaches the
production result feed.
"""
from __future__ import annotations

BIAS_PACE_VERSION = "arvexq-bias-pace-v1"

# Fixed by the 2026-11-16 validation (main analysis). Do not tune.
SOURCE_MIN_CORNER_COVERAGE = 0.8
_FRONT_Q_MAX = 1.0 / 3.0
_BACK_Q_MIN = 2.0 / 3.0

_PACE_PHASES = ("start", "corner3", "corner4")

# Summary labelling only (never feeds the numbers): a shrunk bias
# below this magnitude reads as "neutral" in the summary tags.
_TENDENCY_BAND = 0.05


def _int_or_none(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value) if value.is_integer() else None
    if isinstance(value, str) and value.strip().lstrip("+").isdigit():
        return int(value.strip())
    return None


def _corner1(finisher):
    """The finisher's first-corner position, or None when the
    record carries none (empty / malformed cornerPositions)."""
    if not isinstance(finisher, dict):
        return None
    corners = finisher.get("cornerPositions")
    if not isinstance(corners, list) or not corners:
        return None
    pos = _int_or_none(corners[0])
    return pos if pos is not None and pos > 0 else None


def _order_key(race):
    """A comparable ordering key for a race on the day card:
    ("time", "HH:MM") when a start time is recorded, else
    ("no", race number). Keys of different kinds never compare —
    a race whose order against the target cannot be established
    is excluded rather than risk leaking a later race."""
    if not isinstance(race, dict):
        return None
    start = race.get("startTime")
    if isinstance(start, str) and start.strip():
        return ("time", start.strip())
    number = _int_or_none(race.get("raceNo"))
    if number is not None:
        return ("no", number)
    return None


def _is_source_race(target, race):
    """Same date, same track, provably earlier on the card, and
    not the target race itself."""
    if not isinstance(race, dict) or race is target:
        return False
    if race.get("date") != target.get("date"):
        return False
    if race.get("track") != target.get("track"):
        return False
    target_key = _order_key(target)
    race_key = _order_key(race)
    if target_key is None or race_key is None:
        return False
    if target_key[0] != race_key[0]:
        return False
    return race_key[1] < target_key[1]


def _race_pools(finishers):
    """One source race's contribution to the bias pools, or None
    when the race does not qualify (no result, or first-corner
    coverage under the fixed 80% gate).

    Returns (pools, field_size) where pools counts starters and
    top-3 finishers per group. FB groups need a first-corner
    position; IO groups need only the horse number, so a race can
    feed IO for every finisher while feeding FB only for the
    finishers whose cornerPositions are recorded."""
    if not isinstance(finishers, list):
        return None
    rows = []
    for finisher in finishers:
        if not isinstance(finisher, dict):
            continue
        finish = _int_or_none(finisher.get("finish"))
        number = _int_or_none(finisher.get("horseNumber"))
        if finish is None or finish <= 0 or number is None:
            continue
        rows.append((number, finish, _corner1(finisher)))
    if not rows:
        return None
    field_size = len(rows)
    with_corner = sum(1 for _, _, c in rows if c is not None)
    if with_corner / field_size < SOURCE_MIN_CORNER_COVERAGE:
        return None
    pools = {
        "frontStarters": 0, "frontTop3": 0,
        "backStarters": 0, "backTop3": 0,
        "innerStarters": 0, "innerTop3": 0,
        "outerStarters": 0, "outerTop3": 0,
    }
    for number, finish, corner1 in rows:
        top3 = 1 if finish <= 3 else 0
        ratio = number / field_size
        if ratio <= _FRONT_Q_MAX:
            pools["innerStarters"] += 1
            pools["innerTop3"] += top3
        elif ratio > _BACK_Q_MIN:
            pools["outerStarters"] += 1
            pools["outerTop3"] += top3
        if corner1 is None:
            continue
        q = corner1 / field_size
        if q <= _FRONT_Q_MAX:
            pools["frontStarters"] += 1
            pools["frontTop3"] += top3
        elif q > _BACK_Q_MIN:
            pools["backStarters"] += 1
            pools["backTop3"] += top3
    return pools, field_size


def _rate_diff(pools, group_a, group_b):
    """top-3 rate(a) - top-3 rate(b), or None when either group
    is empty (the difference is then not measurable, not zero)."""
    a_starters = pools[group_a + "Starters"]
    b_starters = pools[group_b + "Starters"]
    if a_starters == 0 or b_starters == 0:
        return None
    return pools[group_a + "Top3"] / a_starters - pools[group_b + "Top3"] / b_starters


def compute_same_day_bias(target_race, day_races) -> dict:
    """The day's bias at the target race's track, from the races
    that finished before it on the same card.

    target_race / day_races entries: {"date", "track", "raceNo",
    "startTime", "finishers": [...]} as described in the module
    docstring. day_races may contain the target race itself and
    races from other tracks/dates; they are filtered out.

    Returns {"version", "available", "status", "frontBack",
    "insideOutside", "rawFrontBack", "rawInsideOutside",
    "sampleRaces", "strength", "sourceRaceNos", "pools"}.
    frontBack / insideOutside are the shrunk values (raw * w).
    When no source race qualifies, available is False, the biases
    are exactly 0.0 and the raw values are None: an explicit
    neutral, never an estimate."""
    empty = {
        "version": BIAS_PACE_VERSION,
        "available": False,
        "status": "no-source-races",
        "frontBack": 0.0,
        "insideOutside": 0.0,
        "rawFrontBack": None,
        "rawInsideOutside": None,
        "sampleRaces": 0,
        "strength": 0.0,
        "sourceRaceNos": [],
        "pools": None,
    }
    if not isinstance(target_race, dict) or not isinstance(day_races, list):
        return empty
    totals = None
    source_nos = []
    sample = 0
    for race in day_races:
        if not _is_source_race(target_race, race):
            continue
        got = _race_pools(race.get("finishers"))
        if got is None:
            continue
        pools, _field = got
        sample += 1
        if totals is None:
            totals = dict(pools)
        else:
            for key in totals:
                totals[key] += pools[key]
        number = _int_or_none(race.get("raceNo"))
        if number is not None:
            source_nos.append(number)
    if totals is None:
        return empty
    strength = sample / (sample + 2.0)
    raw_fb = _rate_diff(totals, "front", "back")
    raw_io = _rate_diff(totals, "inner", "outer")
    return {
        "version": BIAS_PACE_VERSION,
        "available": True,
        "status": "ok",
        "frontBack": (raw_fb if raw_fb is not None else 0.0) * strength,
        "insideOutside": (raw_io if raw_io is not None else 0.0) * strength,
        "rawFrontBack": raw_fb,
        "rawInsideOutside": raw_io,
        "sampleRaces": sample,
        "strength": strength,
        "sourceRaceNos": sorted(source_nos),
        "pools": totals,
    }


def pace_positions_from_forecast(pace_entry) -> dict:
    """Per-horse forecast positions {number: {phase: {"rank",
    "pct"}}} from one race's pace-forecast.json entry.

    Mirrors the materials builder's convention exactly: rank runs
    sequentially through the phase's groups from the forecast
    front (group order, then order within the group) and
    pct = rank / the phase's own horse count. A phase that is
    missing or malformed is absent; nothing is estimated."""
    out: dict = {}
    if not isinstance(pace_entry, dict):
        return out
    positions = pace_entry.get("positions")
    if not isinstance(positions, dict):
        return out
    for phase in _PACE_PHASES:
        groups = positions.get(phase)
        if not isinstance(groups, list):
            continue
        flat: list = []
        for group in groups:
            if not isinstance(group, list):
                continue
            for number in group:
                number = _int_or_none(number)
                if number is not None:
                    flat.append(number)
        if not flat:
            continue
        field = len(flat)
        for idx, number in enumerate(flat):
            rank = idx + 1
            out.setdefault(number, {})[phase] = {
                "rank": rank,
                "pct": rank / field,
            }
    return out


def _frame_score(number, field_size):
    """+1 inner / 0 middle / -1 outer by horse-number ratio —
    the same frame score the 2026-11-16 validation overlaid."""
    if number is None or not field_size:
        return None
    ratio = number / field_size
    if ratio <= _FRONT_Q_MAX:
        return 1
    if ratio > _BACK_Q_MIN:
        return -1
    return 0


def _tendency(value, positive, negative):
    if value >= _TENDENCY_BAND:
        return positive
    if value <= -_TENDENCY_BAND:
        return negative
    return "neutral"


def overlay_bias_on_pace(bias, pace_positions, field_size=None) -> dict:
    """Overlay a computed bias on the pace forecast, per horse.

    bias: the dict from compute_same_day_bias. pace_positions:
    {number: {phase: {"rank", "pct"}}} (materials form; build it
    from a pace-forecast.json entry with
    pace_positions_from_forecast). field_size: the target race's
    runner count for the frame score; defaults to the number of
    horses carrying a forecast position.

    Returns {"version", "available", "bias": {...echo...},
    "horses": {number: {"adjustment", "frontBackComponent",
    "insideOutsideComponent", "positionPct", "frontness",
    "frameScore"}}, "summary": {...}}.

    A horse with no forecast position carries no adjustment
    (None components, 0.0 is never invented for it); a race whose
    bias is unavailable gives every positioned horse an adjustment
    of exactly 0.0."""
    bias = bias if isinstance(bias, dict) else {}
    fb = bias.get("frontBack") or 0.0
    io = bias.get("insideOutside") or 0.0
    available = bool(bias.get("available"))
    positions = pace_positions if isinstance(pace_positions, dict) else {}
    if not field_size:
        field_size = len(positions)
    horses: dict = {}
    for raw_number, phases in positions.items():
        number = _int_or_none(raw_number)
        if number is None or not isinstance(phases, dict):
            continue
        pcts = []
        for phase in _PACE_PHASES:
            cell = phases.get(phase)
            if isinstance(cell, dict):
                pct = cell.get("pct")
                if isinstance(pct, (int, float)) and not isinstance(pct, bool):
                    pcts.append(float(pct))
        frame = _frame_score(number, field_size)
        if not pcts:
            horses[number] = {
                "adjustment": None,
                "frontBackComponent": None,
                "insideOutsideComponent": None,
                "positionPct": None,
                "frontness": None,
                "frameScore": frame,
            }
            continue
        position_pct = sum(pcts) / len(pcts)
        frontness = (0.5 - position_pct) * 2.0
        fb_component = fb * frontness if available else 0.0
        io_component = io * frame if (available and frame is not None) else 0.0
        horses[number] = {
            "adjustment": fb_component + io_component,
            "frontBackComponent": fb_component,
            "insideOutsideComponent": io_component,
            "positionPct": position_pct,
            "frontness": frontness,
            "frameScore": frame,
        }
    ranked = sorted(
        ((h["adjustment"], n) for n, h in horses.items()
         if h["adjustment"] is not None),
        reverse=True,
    )
    fb_tendency = _tendency(fb, "front", "closer") if available else "neutral"
    io_tendency = _tendency(io, "inside", "outside") if available else "neutral"
    tags = []
    if not available:
        tags.append("no-bias")
    else:
        if fb_tendency == "front":
            tags.append("front-favourable")
        elif fb_tendency == "closer":
            tags.append("closer-favourable")
        if io_tendency == "inside":
            tags.append("inside-favourable")
        elif io_tendency == "outside":
            tags.append("outside-favourable")
        if not tags:
            tags.append("neutral-bias")
    summary = {
        "frontBackTendency": fb_tendency,
        "insideOutsideTendency": io_tendency,
        "tags": tags,
        "mostAdvantaged": [n for _, n in ranked[:3]],
        "mostDisadvantaged": [n for _, n in ranked[-3:]][::-1] if ranked else [],
    }
    return {
        "version": BIAS_PACE_VERSION,
        "available": available and bool(horses),
        "bias": {
            "frontBack": fb,
            "insideOutside": io,
            "sampleRaces": bias.get("sampleRaces", 0),
            "strength": bias.get("strength", 0.0),
        },
        "horses": horses,
        "summary": summary,
    }


def bias_adjusted_pace(target_race, day_races, pace_entry,
                       field_size=None) -> dict:
    """End-to-end convenience: the day's bias at the target race
    plus its overlay on that race's pace-forecast.json entry.

    Returns {"bias": compute_same_day_bias(...), "overlay":
    overlay_bias_on_pace(...)}. field_size defaults to the pace
    entry's recorded runner count when present."""
    bias = compute_same_day_bias(target_race, day_races)
    positions = pace_positions_from_forecast(pace_entry)
    if not field_size and isinstance(pace_entry, dict):
        field_size = _int_or_none(pace_entry.get("n_runners"))
    overlay = overlay_bias_on_pace(bias, positions, field_size)
    return {"bias": bias, "overlay": overlay}
