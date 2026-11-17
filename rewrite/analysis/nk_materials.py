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

With the frozen DEFAULT_WEIGHTS the terms that can move a
probability from the materials this lane actually receives are
``comment`` (0.25), ``grade`` (0.20) and ``speed`` (0.15): the
forward NAR collection carries no stable comments or training
grades (those pages do not exist for NAR), so on current data the
active speed term is the speed residual — what netkeiba's index
sees beyond our own spd2.

Course terms (v2, 2026-11-17, explicit user instruction: a
weight of zero is meaningless — wire the course analysis in
properly). The construction is the one the 2026-11-16 overlay
validation measured (validate_overlays.py on the walk-forward
corpus, NAR test 257R: top-1 +3.9pt, date-cluster 95% CI lower
bound above 0, winner log-loss improved):

    course_front = course_front_bias * (front_rate - race mean)
    course_frame = frame-group bias of the horse's own frame

with front_rate the validation's own definition (recency-weighted
share of past runs whose first-corner position ratio is at most
1/3, computed here from the race record's past runs) and the
frame groups inner (frames 1-2) / mid (3-5) / outer (6+). The
bias ESTIMATOR differs from the validation's, by necessity: the
validation shrank our own corpus's walk-forward counts, while
this lane has no results corpus — so the biases are read from
the netkeiba course-analysis tables the collection delivers for
this race's own course (top-3 rate of the front styles 逃/先
minus the back styles 差/追; each frame group's top-3 rate minus
the course's overall top-3 rate). Those tables aggregate
thousands of runs per course, far beyond the validation's
40-run minimum cell, so no shrinkage is applied. The weights are
NOT invented: a coordinate-descent grid search on winner
log-loss over the validation corpus's fit+calib races only
(NAR fit 703 + calib 142; the test segment was never touched)
selects course_front +0.10 / course_frame +0.05 — the same point
the 2026-11-16 run learned on its train split and froze for the
test quoted above; learned on fit alone, the same weights also
improved the held-out calib winner log-loss (255.70 vs 257.72
at zero). JRA learned the opposite sign on its fit+calib
(front -0.25 / frame 0, matching its negative test result), so
in v2 the course weights applied to NAR races only and JRA kept
the frozen defaults (course terms inert).

v3 (2026-11-17, the user's follow-up instruction: "あらたに
やってみんとわからんやろ" — you cannot know without actually
trying it): the NAR weights now ALSO apply to JRA, as a marked
TRIAL. The provenance is the re-measurement of JRA with THIS
lane's own feature definitions (course-weights-20261117
REPORT.md §7): a JRA-specific grid search over JRA fit/calib
found no stable weight (fit picked front +0.05, which then
worsened the held-out calib; fit+calib flipped to -0.05 on a
near-flat surface), so no JRA-learned weight is adopted. But
the NAR weights (+0.10 / +0.05), applied unchanged to the JRA
test segment (44 races, 2026-11-07/08), improved all three
metrics over v9b (top-1 36.4% -> 40.9%, NDCG@3 +0.0129,
winner log-loss -0.0080, non-negative on both days). That is a
post-hoc observation on two days of test data — NOT a
validated JRA weight — so the JRA course terms ship as a trial
(the stamp's weights label records the trial and this
provenance) and are to be judged on forward JRA racing. NAR is
unchanged: same weights, same label, same numbers. The v3 bump
re-issues a v2-stamped pre-post JRA race exactly once under
the trial; NAR races re-stamped by the same bump recompute
identically.

Pace term (v4, 2026-11-17, same user instruction — put ALL of
the collected data in): the netkeiba AI pace forecast's
per-horse forecast positions (start / 3-corner / 4-corner group
diagrams, collected forward into pace-forecast.json and carried
through the materials file per horse as forecast position rank
and percentile per phase, plus the race's pace label) enter as
one more integrated-evaluation term:

    pace_score(h) = sign(label) * (pct4(h) - 0.5) * 2

with pct4 the horse's forecast 4-corner position percentile
(0 = forecast to lead, 1 = forecast last) and sign +1 for a
high-pace label (H), -1 for a slow label (S), and no score at
all for any other label (M included: a middling pace forecast
says nothing about who the shape favours). Reading: in a
high-pace race the forecast front-runners are expected to be
cooked by the pressure, so the score rewards the horses
forecast to sit behind them; in a slow race it rewards the
front. integrate() z-scores the score within the race as usual.

HONESTY, recorded here and in the PR body: this term is
UNVALIDATED. The AI pace-forecast diagrams exist only around
race day (the pages do not persist), so NO historical pace-
forecast data exists and a retrospective validation is
impossible — the term ships on the user's explicit instruction
to put all collected data in, at a trial weight of 0.10 (the
same order as the other material terms), stamped
pace-trial-20261117(w=0.10;unvalidated-no-history) on every
publication it touches, to be judged on forward racing only.

A race with no materials entry, or whose entry cannot produce a
single nonzero term (fewer than three horses with an index — the
z-scores need three), is returned byte-identical: the adjustment
never invents a value and never partially applies.
"""
from __future__ import annotations

from ..safety.probability import distribution, marginals
from .ability import RECENCY_DECAY
from .forecast import RaceForecast, RunnerForecast, _assign_marks
from .integrated_eval import DEFAULT_WEIGHTS, integrate

NK_MATERIALS_VERSION = "nk-materials-v4"
NK_WEIGHTS_LABEL = "integrated-eval-defaults-20261116"
# Course-term weights for NAR races, selected on fit+calib only
# (see the module docstring).
COURSE_WEIGHTS_NAR = {"course_front": 0.10, "course_frame": 0.05}
NK_COURSE_WEIGHTS_LABEL = "course-nar-fitcalib-20261117(front+0.10/frame+0.05)"
# JRA trial (v3): the SAME weights as NAR, applied to JRA races
# as a trial — NOT learned from JRA data (a JRA-specific search
# found no stable weight). Provenance: course-weights-20261117
# REPORT.md §7 — the NAR weights improved the JRA test segment
# (44R, two days) post-hoc on all three metrics. The label
# records the trial and its source in every stamp these terms
# touch; forward JRA results decide whether the trial stays.
COURSE_WEIGHTS_JRA_TRIAL = {"course_front": 0.10, "course_frame": 0.05}
NK_COURSE_WEIGHTS_JRA_TRIAL_LABEL = (
    "course-jra-trial-20261117(front+0.10/frame+0.05;"
    "nar-weights;source=course-weights-report-sec7)")
# The publish lane passes race.segment.value, whose JRA flat
# spelling is "jra_flat"; "jra" is accepted as the same segment
# (the spelling the adapter's callers and tests use for JRA).
JRA_SEGMENTS = ("jra", "jra_flat")

# Pace term (v4): TRIAL weight, UNVALIDATED — no historical AI
# pace-forecast data exists, so no retrospective validation is
# possible (see the module docstring). Same order of magnitude
# as the other material terms (speed 0.15 / course_front 0.10).
# The label is stamped on every publication the term touches.
PACE_WEIGHT = 0.10
NK_PACE_WEIGHTS_LABEL = "pace-trial-20261117(w=0.10;unvalidated-no-history)"
_PACE_SIGNS = {"H": 1.0, "S": -1.0}
_PACE_PHASES = ("start", "corner3", "corner4")

_SPEED_COLUMNS = ("nk_best", "nk_avg5", "nk_dist", "nk_course")


def _num(value):
    """A finite int/float or None; bools and strings are not data."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value


def _parse_pace(values) -> dict | None:
    """One horse's pace-forecast positions from the materials
    entry: {phase: {"rank": float, "pct": float}} over the phases
    that carry readable numbers. None when nothing readable —
    the horse simply carries no pace material."""
    if not isinstance(values, dict):
        return None
    out: dict = {}
    for phase in _PACE_PHASES:
        cell = values.get(phase)
        if not isinstance(cell, dict):
            continue
        rank = _num(cell.get("rank"))
        pct = _num(cell.get("pct"))
        if rank is None or pct is None:
            continue
        out[phase] = {"rank": rank, "pct": pct}
    return out or None


def pace_score(pace, label):
    """The pace term's raw score in [-1, 1] (see the module
    docstring): sign(label) * (corner4 percentile - 0.5) * 2.
    None when the label carries no direction (M / unknown) or
    the horse has no 4-corner forecast position."""
    sign = _PACE_SIGNS.get(label) if isinstance(label, str) else None
    if sign is None or not isinstance(pace, dict):
        return None
    cell = pace.get("corner4")
    if not isinstance(cell, dict):
        return None
    pct = _num(cell.get("pct"))
    if pct is None:
        return None
    return sign * (pct - 0.5) * 2.0


def parse_materials_payload(payload) -> dict:
    """Normalise one date's nk-materials payload to
    {arvexq_race_id: {"netkeibaRaceId": str|None,
                      "horses": {int: {column: value}},
                      "courseAnalysis": dict|None,
                      "paceLabel": str|None}}.

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
                horse["pace"] = _parse_pace(values.get("pace"))
                horses[number] = horse
        course = entry.get("courseAnalysis")
        label = entry.get("paceLabel")
        out[str(race_id)] = {
            "netkeibaRaceId": entry.get("netkeibaRaceId"),
            "horses": horses,
            "courseAnalysis": course if isinstance(course, dict) else None,
            "paceLabel": label if isinstance(label, str) else None,
        }
    return out


def speed_coverage(entry) -> int:
    """Horses in the entry carrying the representative index
    (nk_avg5) — the coverage the speed term stands on."""
    if not isinstance(entry, dict):
        return 0
    return sum(1 for h in (entry.get("horses") or {}).values()
               if isinstance(h, dict) and h.get("nk_avg5") is not None)


# ------------------------------------------------- course terms
_FRONT_STYLE_LABELS = ("逃", "先")
_BACK_STYLE_LABELS = ("差", "追")


def _count(value):
    """A count from a collected table cell: numbers pass, digit
    strings are read, anything else is not data."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip().replace(",", ""))
        except ValueError:
            return None
    return None


def _table_cells(table) -> dict:
    """{label: (top3_count, runs)} from one collected netkeiba
    aggregate table ({"見出し": [...], "行": [[...], ...]}).
    Column positions are found by header name, never assumed;
    a row whose counts cannot be read is dropped, never imputed."""
    if not isinstance(table, dict):
        return {}
    headers = table.get("見出し")
    rows = table.get("行")
    if not isinstance(headers, list) or not isinstance(rows, list):
        return {}

    def col(name):
        try:
            return headers.index(name)
        except ValueError:
            return None

    idx = (col("1着"), col("2着"), col("3着"), col("出走回数"))
    if any(i is None for i in idx):
        return {}
    out: dict = {}
    for row in rows:
        if not isinstance(row, list) or not row:
            continue
        label = row[0]
        if not isinstance(label, str):
            continue
        vals = [_count(row[i]) if i < len(row) else None for i in idx]
        if any(v is None for v in vals):
            continue
        out[label.strip()] = (vals[0] + vals[1] + vals[2], vals[3])
    return out


def _frame_group(frame):
    """The validation's frame groups, by frame number."""
    if frame is None:
        return None
    if frame <= 2:
        return "inner"
    if frame <= 5:
        return "mid"
    return "outer"


def _frame_number(label: str):
    digits = ""
    for ch in label:
        if ch.isdigit():
            digits += ch
        elif digits:
            break
    return int(digits) if digits else None


def course_biases(course_analysis):
    """(front_bias, {frame_group: frame_bias}) for ONE race's
    course, read from the collected netkeiba course-analysis
    tables of that race's materials entry.

    front_bias = top-3 rate of the front styles (逃/先) minus
    the top-3 rate of the back styles (差/追); frame_bias[g] =
    group g's top-3 rate minus the course's overall top-3 rate.
    A side with no readable rows yields None / an absent group —
    the corresponding horses simply carry no course value.
    """
    if not isinstance(course_analysis, dict):
        return None, {}
    styles = _table_cells(course_analysis.get("有利な脚質"))
    front_bias = None
    f_top3 = sum(styles[l][0] for l in _FRONT_STYLE_LABELS if l in styles)
    f_runs = sum(styles[l][1] for l in _FRONT_STYLE_LABELS if l in styles)
    b_top3 = sum(styles[l][0] for l in _BACK_STYLE_LABELS if l in styles)
    b_runs = sum(styles[l][1] for l in _BACK_STYLE_LABELS if l in styles)
    if f_runs > 0 and b_runs > 0:
        front_bias = f_top3 / f_runs - b_top3 / b_runs
    frame_bias: dict = {}
    frames = _table_cells(course_analysis.get("有利な枠順"))
    if frames:
        tot_top3 = sum(v[0] for v in frames.values())
        tot_runs = sum(v[1] for v in frames.values())
        if tot_runs > 0:
            overall = tot_top3 / tot_runs
            groups: dict = {}
            for label, (top3, runs) in frames.items():
                group = _frame_group(_frame_number(label))
                if group is None:
                    continue
                cell = groups.setdefault(group, [0.0, 0.0])
                cell[0] += top3
                cell[1] += runs
            for group, (top3, runs) in groups.items():
                if runs > 0:
                    frame_bias[group] = top3 / runs - overall
    return front_bias, frame_bias


def front_rate_from_runs(past_runs):
    """The validation's front_rate, verbatim: the recency-weighted
    share of a horse's past runs whose first-corner position
    ratio (position / field size) is at most 1/3. Weights are
    RECENCY_DECAY ** (index in the full past-run list, newest
    first) — runs without corner evidence consume their index,
    exactly as the round-2 builder's enumerate did. None when no
    past run carries corner evidence."""
    pairs = []
    for idx, run in enumerate(past_runs or ()):
        corners = run.corner_positions
        field = run.field_size.value if run.field_size is not None else None
        if not corners or not isinstance(field, (int, float)) or field < 2:
            continue
        ratio = corners[0] / field
        pairs.append((1.0 if ratio <= 1.0 / 3 else 0.0,
                      RECENCY_DECAY ** idx))
    if not pairs:
        return None
    total_w = sum(w for _, w in pairs)
    if total_w <= 0:
        return None
    return sum(v * w for v, w in pairs) / total_w


def course_inputs_from_race(race) -> dict:
    """{number: {"front_rate": float|None, "frame": int|None}}
    for the race's non-scratched runners, from the race record
    itself (the same record the pace layer reads)."""
    out: dict = {}
    for r in race.runners:
        if r.scratched:
            continue
        frame = r.frame_number.value if r.frame_number is not None else None
        out[r.number] = {
            "front_rate": front_rate_from_runs(r.past_runs),
            "frame": (int(frame) if isinstance(frame, (int, float))
                      and not isinstance(frame, bool) else None),
        }
    return out


def apply_nk_materials(forecast: RaceForecast, entry,
                       extras_by_number: dict | None = None,
                       segment: str | None = None,
                       course_inputs: dict | None = None):
    """Apply the integrated-evaluation adjustment to a v9b
    RaceForecast. Returns (forecast, info); when nothing can
    contribute, the SAME forecast object is returned with
    info["applied"] False. Deterministic: same inputs, same
    outputs (integrate() is closed-form over the runners in
    forecast order).

    Course terms are computed only when segment is "nar" or a
    JRA segment (see JRA_SEGMENTS) and course_inputs (see
    course_inputs_from_race) are supplied: the biases come from
    the entry's own courseAnalysis tables, the per-horse front
    rates and frames from the race record. NAR uses the
    fit+calib-selected weights; JRA uses the same values as a
    marked trial (COURSE_WEIGHTS_JRA_TRIAL — when the trial's
    terms contribute, info["courseTrial"] is "jra" and the
    weights label carries the trial label). Any other segment —
    or a race without course inputs — runs with the frozen
    defaults, where the course weights are 0.

    The pace term (v4) is segment-independent: it contributes
    whenever the entry carries pace-forecast positions and a
    directional pace label (H / S), at the UNVALIDATED trial
    weight PACE_WEIGHT; when it contributes, info["paceTrial"]
    is set and the weights label carries NK_PACE_WEIGHTS_LABEL.
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
    is_jra = segment in JRA_SEGMENTS
    course_active = ((segment == "nar" or is_jra)
                     and isinstance(course_inputs, dict))
    front_bias, frame_bias = (course_biases(entry.get("courseAnalysis"))
                              if course_active else (None, {}))
    horses = []
    for r in forecast.runners:
        base = r.strength if r.strength is not None else r.p_win
        if base is None or base <= 0:
            continue
        mat = materials.get(r.number) or {}
        extra = extras_by_number.get(r.number) or {}
        spd2_recent = _num(extra.get("spd2_recent"))
        horse = {
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
            # AI pace-forecast position term (v4, UNVALIDATED
            # trial — see the module docstring).
            "pace_score": pace_score(mat.get("pace"),
                                     entry.get("paceLabel")),
        }
        if course_active:
            ci = course_inputs.get(r.number) or {}
            horse["front_rate"] = ci.get("front_rate")
            horse["_frame_group"] = _frame_group(ci.get("frame"))
        horses.append(horse)
    if len(horses) < 3:
        return forecast, info
    weights = None
    course_label = None
    if course_active and (front_bias is not None or frame_bias):
        frs = [h["front_rate"] for h in horses
               if h.get("front_rate") is not None]
        mean_fr = sum(frs) / len(frs) if frs else None
        for h in horses:
            fr = h.get("front_rate")
            h["course_front"] = (
                front_bias * (fr - mean_fr)
                if front_bias is not None and fr is not None
                and mean_fr is not None else None)
            h["course_frame"] = frame_bias.get(h.get("_frame_group"))
        if is_jra:
            weights = dict(COURSE_WEIGHTS_JRA_TRIAL)
            course_label = NK_COURSE_WEIGHTS_JRA_TRIAL_LABEL
        else:
            weights = dict(COURSE_WEIGHTS_NAR)
            course_label = NK_COURSE_WEIGHTS_LABEL
    pace_label_stamp = None
    if any(h.get("pace_score") is not None for h in horses):
        weights = dict(weights) if weights else {}
        weights["pace"] = PACE_WEIGHT
        pace_label_stamp = NK_PACE_WEIGHTS_LABEL
    for h in horses:
        h.pop("_frame_group", None)
    probs, coverage, detail = integrate(horses, weights)
    info["coverage"] = coverage
    extra_labels = []
    if course_label is not None and any(
            k in d["terms"] for d in detail
            for k in ("course_front", "course_frame")):
        extra_labels.append(course_label)
        if is_jra:
            # The trial is on the record wherever the stamp is
            # read from: the weights label above, plus this
            # explicit marker the publish lane copies into the
            # nkMaterials stamp.
            info["courseTrial"] = "jra"
    if pace_label_stamp is not None and any(
            "pace" in d["terms"] for d in detail):
        extra_labels.append(pace_label_stamp)
        # Same record-keeping as the course trial: the publish
        # lane copies this marker into the nkMaterials stamp so
        # the unvalidated pace trial's forward record stays
        # separable.
        info["paceTrial"] = "ai-pace-forecast"
    if extra_labels:
        info["weights"] = NK_WEIGHTS_LABEL + "+" + "+".join(extra_labels)
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
