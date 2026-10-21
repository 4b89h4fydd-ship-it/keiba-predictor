"""NAR pre-off contextual features from existing facts; no new acquisition/model route.

Race-level sectionals are never represented as individual horse gate speed.
Every observation must precede the race and missing inputs remain absent.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from math import isfinite
from statistics import mean, median
from typing import Any

JST = timezone(timedelta(hours=9))
NAR_CIRCUITS = {"地方", "NAR", "nar", "local"}
JRA_TRACKS = {"札幌", "函館", "福島", "新潟", "東京", "中山", "中京", "京都", "阪神", "小倉"}
TRIP_SOURCES = {"official-stewards", "reviewed-video"}
SECTIONAL_SOURCES = {"official", "reviewed-video"}


def _number(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if isfinite(result) else None


def _day(value: Any) -> date | None:
    try:
        return date.fromisoformat(str(value or "")[:10])
    except (ValueError, TypeError):
        return None


def _instant(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.astimezone(JST) if parsed.tzinfo is not None else None


def _race_off(race: dict[str, Any]) -> datetime | None:
    day = _day(race.get("date"))
    start = str(race.get("startTime") or "")
    if day is None:
        return None
    import re
    match = re.search(r"(?<!\d)([01]?\d|2[0-3]):([0-5]\d)(?!\d)", start)
    if not match:
        return None
    return datetime(day.year, day.month, day.day, int(match[1]), int(match[2]), tzinfo=JST)


def _corners(run: dict[str, Any]) -> list[int]:
    observed = run.get("cornerPositions")
    if isinstance(observed, (list, tuple)):
        values = observed
    elif isinstance(run.get("passing"), str):
        import re
        values = re.findall(r"\d+", run["passing"])
    else:
        values = []
    out = []
    for item in values:
        value = _number(item)
        if value is not None and value >= 1 and value.is_integer():
            out.append(int(value))
    return out


def _historical(runs: list[dict[str, Any]], race: dict[str, Any]) -> list[dict[str, Any]]:
    cutoff = _day(race.get("date"))
    if cutoff is None:
        return []
    rows = [r for r in runs if isinstance(r, dict)
            and (day := _day(r.get("date") or r.get("raceDate"))) is not None and day < cutoff]
    return sorted(rows, key=lambda row: str(row.get("date") or row.get("raceDate")), reverse=True)


def _matched(run: dict[str, Any], race: dict[str, Any]) -> bool:
    distance, old_distance = _number(race.get("distance")), _number(run.get("distance"))
    track = str(race.get("track") or "")
    surface = str(race.get("surface") or "")
    condition = str(race.get("condition") or race.get("going") or "")
    return bool(track and surface and condition and distance is not None
                and old_distance is not None and abs(distance - old_distance) <= 100
                and str(run.get("track") or "") == track
                and str(run.get("surface") or "") == surface
                and str(run.get("condition") or run.get("going") or "") == condition)


def _sectional(run: dict[str, Any]) -> float | None:
    provenance = run.get("sectionalProvenance")
    if not isinstance(provenance, dict):
        return None
    if provenance.get("sourceKind") not in SECTIONAL_SOURCES or not provenance.get("sourceRef"):
        return None
    for key in ("first3FSeconds", "early3FSeconds", "first3F"):
        value = _number(run.get(key))
        if value is not None and 20 <= value <= 60:
            return value
    return None


def _bias(race: dict[str, Any]) -> dict[str, float]:
    """Accept only a versioned, timestamped *pre-off* estimate, never an inferred official fact."""
    estimate = race.get("trackBiasEstimate")
    off = _race_off(race)
    if not isinstance(estimate, dict) or off is None:
        return {}
    captured = _instant(estimate.get("capturedAt"))
    observed = _instant(estimate.get("observedThrough"))
    count = _number(estimate.get("sampleRaces"))
    if not captured or not observed or count is None or count < 3:
        return {}
    if not (observed <= captured < off):
        return {}
    out: dict[str, float] = {}
    for raw, name in (("frontBackScore", "front_back_score"), ("insideOutsideScore", "inside_outside_score")):
        number = _number(estimate.get(raw))
        if number is not None and -1 <= number <= 1:
            out[f"nar::bias::{name}"] = number
    if out:
        out["nar::bias::sample_races"] = count
    return out


def _odds_trend(horse: dict[str, Any], race: dict[str, Any]) -> dict[str, float]:
    """Only frozen official snapshots not later than the original forecast lock."""
    lock = race.get("preRacePrediction")
    fixed = _instant(lock.get("fixedAt")) if isinstance(lock, dict) else None
    off = _race_off(race)
    if not fixed or not off or fixed >= off:
        return {}
    snapshots = horse.get("oddsHistory")
    if not isinstance(snapshots, list):
        return {}
    rows: list[tuple[datetime, float]] = []
    for snapshot in snapshots:
        if not isinstance(snapshot, dict) or snapshot.get("sourceKind") != "official":
            continue
        moment = _instant(snapshot.get("capturedAt"))
        price = _number(snapshot.get("winOdds"))
        if moment is not None and price is not None and price > 1 and moment <= fixed:
            rows.append((moment, price))
    unique = sorted(set(rows))
    if len(unique) < 2 or unique[-1][0] == unique[0][0]:
        return {}
    first, last = unique[0][1], unique[-1][1]
    return {"market::preoff_odds_change_ratio": last / first - 1.0,
            "market::preoff_odds_observations": float(len(unique))}


def build_nar_context_features(
    horse: dict[str, Any], race: dict[str, Any], runs: list[dict[str, Any]]
) -> dict[str, float]:
    """Sparse NAR-only addendum to the shared six-system feature pipeline.

    No guessed trip incident, no cross-condition raw split-time comparison,
    no post-off observation, and no weights, mark or ticket decisions.
    """
    if (str(race.get("circuit") or "") not in NAR_CIRCUITS
            or "帯広" in str(race.get("track") or "")):
        return {}
    prior = _historical(runs, race)
    out: dict[str, float] = {}
    recent = prior[:5]
    first_corner: list[float] = []
    front: list[float] = []
    fades: list[float] = []
    for run in recent:
        positions = _corners(run)
        field = _number(run.get("fieldSize"))
        finish = _number(run.get("finish"))
        if not positions or field is None or field < 2 or positions[0] > field:
            continue
        first_corner.append((positions[0] - 1) / (field - 1))
        is_front = positions[0] <= max(2, int((field + 2) // 3))
        front.append(float(is_front))
        if is_front and finish is not None and 1 <= finish <= field:
            fades.append(float(finish > max(3, int(field * 2 / 3))))
    if first_corner:
        out["nar::pace::early_position_mean_w5"] = mean(first_corner)
        out["nar::pace::first_corner_samples_w5"] = float(len(first_corner))
        out["nar::pace::front_rate_w5"] = mean(front)
    if fades:
        out["nar::pace::front_fade_rate_w5"] = mean(fades)

    # This is *race-level* pace context of comparable historical races only.
    # It is deliberately not labeled as the individual's early speed.
    comparable = [_sectional(r) for r in prior if _matched(r, race)]
    laps = [v for v in comparable if v is not None][:5]
    if laps:
        out["nar::sectional::comparable_race_first3f_median_w5"] = median(laps)
        out["nar::sectional::comparable_race_sample_w5"] = float(len(laps))

    # Explicitly reviewed historical trip observations, never guessed from finishing position.
    trip: dict[str, list[float]] = {k: [] for k in ("wideTrip", "kickback", "blocked", "slowStart")}
    for run in recent:
        observed = run.get("tripObservations")
        if not isinstance(observed, dict) or observed.get("sourceKind") not in TRIP_SOURCES or not observed.get("sourceRef"):
            continue
        for key, values in trip.items():
            if isinstance(observed.get(key), bool):
                values.append(float(observed[key]))
    for key, values in trip.items():
        if values:
            out[f"nar::trip::{key}_rate_w5"] = mean(values)
            out[f"nar::trip::{key}_samples_w5"] = float(len(values))

    if prior:
        prev_jockey = str(prior[0].get("jockey") or "").strip()
        current_jockey = str(horse.get("jockey") or "").strip()
        if prev_jockey and current_jockey:
            out["nar::jockey::changed_from_previous"] = float(prev_jockey != current_jockey)
        old_track = str(prior[0].get("track") or "").strip()
        if old_track:
            out["nar::transfer::last_run_jra"] = float(old_track in JRA_TRACKS)

    out.update(_bias(race))
    out.update(_odds_trend(horse, race))
    return out
