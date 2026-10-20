"""Ability evidence: no outcomes, tactical adjustments or probability mapping."""
from datetime import date
from statistics import median
import math


def prior_runs(horse, cutoff):
    date.fromisoformat(cutoff)
    by_day = {}
    for row in horse.get("recentRaces") or []:
        day = row.get("_raceDate") or row.get("date")
        try:
            if not isinstance(day, str) or date.fromisoformat(day).isoformat() != day or day >= cutoff:
                continue
        except ValueError:
            continue
        if day in by_day and by_day[day] != row:
            # Distinct conflicting starts are not silently averaged.
            raise ValueError("conflicting same-day history")
        by_day[day] = row
    return [by_day[d] for d in sorted(by_day, reverse=True)]


def quality(row):
    n, f = row.get("fieldSize"), row.get("finish")
    if type(n) is not int or n < 2 or type(f) not in (int, float):
        return None
    return (n-f)/(n-1) if math.isfinite(f) and 1 <= f <= n else None


def score_field(histories, method="baseline"):
    if method not in ("baseline", "recent5", "recent5_shrunk"):
        raise ValueError("unknown ability method")
    values = {}
    counts = {}
    for no, rows in histories.items():
        qs = [q for row in rows if (q := quality(row)) is not None]
        if not qs:
            values[no], counts[no] = None, 0
            continue
        if method == "baseline":
            values[no], counts[no] = sum(qs)/len(qs), len(qs)
        else:
            qs = qs[:5]
            weights = list(range(5, 5-len(qs), -1))
            values[no] = sum(q*w for q,w in zip(qs, weights))/sum(weights)
            counts[no] = len(qs)
    if method == "recent5_shrunk":
        observed = [v for v in values.values() if v is not None]
        prior = median(observed) if observed else None
        values = {no: (counts[no]*v+3*prior)/(counts[no]+3) if v is not None else None
                  for no,v in values.items()}
    return values
