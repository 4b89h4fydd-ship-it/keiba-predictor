"""netkeiba materials adjustment for the production forecast lane.

Adopted 2026-11-17 by explicit user instruction ("集めたデータは
全部、予想に入れろ" — put ALL of the collected data into the
forecast). The forward collection (netkeiba premium materials,
saved per date by the collection crons) is normalised into
``rewrite/data/nk_materials/<date>.json`` (see
scripts/arvexq_nk_materials_build.py for the format) and this
module applies the integrated evaluation of
``rewrite/analysis/integrated_eval.py`` — vendored verbatim from
the research tree, with its DEFAULT_WEIGHTS frozen — on top of the
v9b probability vector:

    logp_adj(h) = log(p_v9b(h)) + sum_k w_k * z_k(h)
    p_adj       = softmax(logp_adj)

and rebuilds the RaceForecast through the same Plackett-Luce
construction shadow_v9.postprocess_forecast uses, so marks,
tickets, the win/top-3 display and the master shadow all derive
from the adjusted probabilities (one evaluation, no drift).

Material inputs per horse (the speed page's full columns):

    nk_speed  := nk_avg5 （5走平均 — integrated_eval's "netkeiba
                 recent-avg index")
    nk_best / nk_dist / nk_course / nk_recent — carried through to
                 integrate() unchanged (their trend / aptitude
                 terms exist in the formula; their weights are 0
                 in the frozen defaults, so today they contribute
                 nothing — the data path is live, the weights are
                 the integrated evaluation's own)
    spd2      := -spd2_recent from the v8 extras. The extras store
                 spd2 as a seconds-like DEFICIT (lower = faster =
                 better, see shadow_v8.LOWER_IS_BETTER_V8), while
                 integrated_eval's residual z(nk) - z(spd2) is
                 defined on a higher-is-better own-speed index;
                 the negation is the whole conversion (z-scores are
                 affine-invariant apart from the sign).

With the frozen DEFAULT_WEIGHTS the only terms that can move a
probability from the materials this lane actually receives are
``comment`` (0.25), ``grade`` (0.20) and ``speed`` (0.15): the
forward NAR collection carries no stable comments or training
grades (those pages do not exist for NAR), so on current data the
active term is the speed residual — what netkeiba's index sees
beyond our own spd2. The course-analysis block is transported in
the same file and recorded in the coverage stamp; its terms
(course_front / course_frame) sit at weight 0 in the frozen
defaults, exactly as the integrated evaluation defines them.

A race with no materials entry, or whose entry cannot produce a
single nonzero term (fewer than three horses with an index — the
z-scores need three), is returned byte-identical: the adjustment
never invents a value and never partially applies.
"""
from __future__ import annotations

from ..safety.probability import distribution, marginals
from .forecast import RaceForecast, RunnerForecast, _assign_marks
from .integrated_eval import DEFAULT_WEIGHTS, integrate

NK_MATERIALS_VERSION = "nk-materials-v1"
NK_WEIGHTS_LABEL = "integrated-eval-defaults-20261116"

_SPEED_COLUMNS = ("nk_best", "nk_avg5", "nk_dist", "nk_course")


def _num(value):
    """A finite int/float or None; bools and strings are not data."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value


def parse_materials_payload(payload) -> dict:
    """Normalise one date's nk-materials payload to
    {arvexq_race_id: {"netkeibaRaceId": str|None,
                      "horses": {int: {column: value}},
                      "courseAnalysis": dict|None}}.

    Anything unreadable normalises to {} (no materials for the
    date) or drops the offending race/horse — a malformed entry
    must never take the lane down, and a dropped horse simply
    receives no adjustment term.
    """
    if not isinstance(payload, dict):
        return {}
    races = payload.get("races")
    if not isinstance(races, dict):
        return {}
    out: dict = {}
    for race_id, entry in races.items():
        if not isinstance(entry, dict):
            continue
        raw_horses = entry.get("horses")
        horses: dict = {}
        if isinstance(raw_horses, dict):
            for key, values in raw_horses.items():
                try:
                    number = int(key)
                except (TypeError, ValueError):
                    continue
                if not isinstance(values, dict):
                    continue
                horse = {col: _num(values.get(col))
                         for col in _SPEED_COLUMNS}
                recent = values.get("nk_recent")
                horse["nk_recent"] = (
                    [_num(v) for v in recent]
                    if isinstance(recent, list) else None)
                horses[number] = horse
        course = entry.get("courseAnalysis")
        out[str(race_id)] = {
            "netkeibaRaceId": entry.get("netkeibaRaceId"),
            "horses": horses,
            "courseAnalysis": course if isinstance(course, dict) else None,
        }
    return out


def speed_coverage(entry) -> int:
    """Horses in the entry carrying the representative index
    (nk_avg5) — the coverage the speed term stands on."""
    if not isinstance(entry, dict):
        return 0
    return sum(1 for h in (entry.get("horses") or {}).values()
               if isinstance(h, dict) and h.get("nk_avg5") is not None)


def apply_nk_materials(forecast: RaceForecast, entry,
                       extras_by_number: dict | None = None):
    """Apply the integrated-evaluation adjustment to a v9b
    RaceForecast. Returns (forecast, info); when nothing can
    contribute, the SAME forecast object is returned with
    info["applied"] False. Deterministic: same inputs, same
    outputs (integrate() is closed-form over the runners in
    forecast order).
    """
    info = {"applied": False, "version": NK_MATERIALS_VERSION,
            "weights": NK_WEIGHTS_LABEL, "coverage": None,
            "netkeibaRaceId": (entry.get("netkeibaRaceId")
                               if isinstance(entry, dict) else None)}
    if forecast.status != "ok" or not isinstance(entry, dict):
        return forecast, info
    materials = entry.get("horses") or {}
    if not materials:
        return forecast, info
    extras_by_number = extras_by_number or {}
    horses = []
    for r in forecast.runners:
        base = r.strength if r.strength is not None else r.p_win
        if base is None or base <= 0:
            continue
        mat = materials.get(r.number) or {}
        extra = extras_by_number.get(r.number) or {}
        spd2_recent = _num(extra.get("spd2_recent"))
        horses.append({
            "num": r.number,
            "v9b": float(base),
            "comment_text": mat.get("comment_text"),
            "grade": mat.get("grade"),
            "nk_speed": mat.get("nk_avg5"),
            "nk_avg5": mat.get("nk_avg5"),
            "nk_best": mat.get("nk_best"),
            "nk_dist": mat.get("nk_dist"),
            "nk_course": mat.get("nk_course"),
            "nk_recent": mat.get("nk_recent"),
            # extras spd2 is a deficit (lower = better); the
            # integrated residual is defined on a higher-is-better
            # own-speed index — negate (see module docstring).
            "spd2": (-spd2_recent if spd2_recent is not None else None),
        })
    if len(horses) < 3:
        return forecast, info
    probs, coverage, detail = integrate(horses)
    info["coverage"] = coverage
    if not any(d["terms"] for d in detail):
        # No term could contribute (e.g. fewer than three horses
        # carry an index, so every z-score is None): the vector
        # would come back identical — report not-applied and keep
        # the original object byte-stable.
        return forecast, info
    # Rebuild through the exact construction postprocess_forecast
    # uses: the adjusted win probabilities ARE the effective PL
    # strengths, so marginals, marks and tickets downstream stay
    # consistent with them.
    pl = marginals(distribution(dict(probs)))
    ranked = sorted(pl, key=lambda n: (-pl[n][0], -pl[n][2], n))
    marks = _assign_marks(ranked, pl)
    runners = []
    for r in forecast.runners:
        if r.number in pl:
            runners.append(RunnerForecast(
                number=r.number, name=r.name,
                ability_score=r.ability_score,
                strength=round(probs[r.number], 6),
                pace_adjustment=r.pace_adjustment,
                pace_reasons=r.pace_reasons,
                p_win=round(pl[r.number][0], 4),
                p_top2=round(pl[r.number][1], 4),
                p_top3=round(pl[r.number][2], 4),
                mark=marks.get(r.number, ""),
                status=r.status,
            ))
        else:
            runners.append(r)
    info["applied"] = True
    info["terms"] = sorted({k for d in detail for k in d["terms"]})
    return RaceForecast(forecast.race_id, forecast.beta,
                        forecast.probability_status, tuple(runners),
                        "ok"), info
