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

All-materials terms (v5, 2026-11-17, the user's repeated
instruction: put EVERYTHING in, now — "はよ全部いれろ"). The
materials file has carried three more per-horse blocks since the
builder's v2 extension (PR #570) that the adapter transported
but never read, plus the newspaper marks the builder carries as
"press". v5 wires all four into the evaluation as plain
within-race z terms, through slots integrated_eval already had
(h2h / mochitime) or gained alongside (press / pedigree):

    mochitime  the horse's best time (seconds) under today's
               conditions, exactly as the data-analysis tab
               computes it (tier 1: same track/surface/distance;
               lower tiers are the builder's recorded fallbacks).
               Raw seconds are z-scored in-race; the weight is
               NEGATIVE (-0.10) because a lower time is better —
               the sign convention integrated_eval's own design
               note prescribes for this slot.
    h2h        the head-to-head ahead rate, shrunk toward the
               neutral 0.5 with prior strength 3 duels:
               (ahead + 3*0.5) / (duels + 3). A horse with one
               lucky duel does not read as a proven dominator,
               and a horse with no duels carries no value at all.
               Weight +0.10.
    pedigree   the sire's record at today's course (sireCourse:
               starts / wins / top-3 from the collected
               course-analysis sire table), shrunk toward a
               generic 10-runner field (win 0.10, top-3 0.30)
               with prior strength 10 starts, scored as the mean
               of the two shrunk rates. A sire with no starts on
               the table carries no value. Weight +0.10.
    press      the newspaper marks, point-scored with the
               research tree's MARK_POINTS (◎5 ○4 ▲3 △2 ☆1,
               消/× 0) and averaged over the marks the collection
               saved for the horse. A race whose collection saved
               no per-horse marks (today's NAR file: press is
               null throughout — the morning collection recorded
               counts only) simply has no press term. Weight
               +0.10.

HONESTY RECORD: unlike the speed residual (frozen research
weights) and the course terms (fit+calib-selected, and for JRA
a marked trial), these four weights are NOT the output of any
retrospective validation — no walk-forward measurement of
bestTime / headToHead / pedigree / press as overlay terms on
v9b exists. They enter at the same magnitude as the other
material terms (0.10) by the user's explicit instruction, as a
marked TRIAL: the stamp's weights label carries
"all-materials-trial-20261117" with each weight whenever any of
the four terms contributes, and forward results are the judge.
(The version steps v3 -> v5 in the merged tree: v4 was the pace
term's version on its own branch; the merged v5 carries both
the pace term below and these four terms, definitions disjoint.)

Pace term (v4, merged into v5, 2026-11-17, same user
instruction — put ALL of
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

v6 terms (2026-11-17, the same user instruction, after the
full audit found them computed but weightless —
eval-full-audit-20261117/forecast-inputs.md #7/#19/#22/#24/
#27/#28). Four more families join, all as marked TRIALS at
magnitude 0.10, none of them validated:

    speed derived  the seven derived features integrated_eval
        has always computed from the speed page's raw columns
        (nk_recent / nk_avg5 / nk_best / nk_dist / nk_course —
        carried in the materials file since v1) and reported in
        coverage, but whose frozen weights were all 0:
        speed_slope (index trend), speed_dev (last run vs own
        5-run average), speed_vol (recent range), speed_sd
        (recent spread), speed_overlap (mean+-sd band overlap
        vs the field), speed_fit (condition fit edge) and
        speed_bias (course-vs-distance aptitude). The signs
        follow integrated_eval's own design notes: slope / dev
        / fit / bias reward the higher value (+0.10); vol / sd
        / overlap are the dispersion family whose documented
        expected sign is negative ("erratic / non-separating
        averages get discounted"), so they enter at -0.10.
        No new data path was needed — the derivation lives
        inside integrate(); v6 only supplies the weights. The
        builder now also reports these features' coverage in
        the materials file's fieldCoverage, computed with
        integrated_eval's own functions.
    combo    the jockey x horse combination record (the pair's
        shrunk top-3 rate together, integrated_eval's
        combo_features). Its data is NOT in the materials file:
        it is computed from the race record itself (each past
        run's jockey, today's jockey) and handed in by the
        publish lane as combo_inputs, exactly like the course
        inputs. Weight +0.10.
    nk judgements  netkeiba's own per-horse judgements —
        nk_form_dev (調子偏差値) and nk_ai (AI予想 score) —
        enter at +0.10 each WHEN the materials file carries
        them (builder fields nkFormDev / nkAiScore). As of
        v6 NO forward collection file carries per-horse values
        for either (the 2026-11-17 / 2026-11-18 collections are
        NAR days, where these pages do not exist, and no JRA
        forward collection exists yet), so today the wiring is
        armed but dataless: the terms contribute nothing and
        no stamp appears until values arrive.
    odds movement  odds_drift (publish-time vs final win odds)
        and odds_wp_gap (final win vs place-range midpoint),
        integrated_eval's odds_movement_features, at +0.10 each
        WHEN the materials file carries a per-horse odds block
        (builder field odds: publishWin / finalWin / placeLow /
        placeHigh). Same status as the judgements: no
        collection file carries the block today (2026-11-17
        recorded forecast odds in its status note only, with no
        file; 2026-11-18 did not collect odds at all), so the
        wiring is armed but dataless.

    closing (上がり3F) — the gap recorded in v6, wired in v7
        (2026-11-18): the production past-run record now
        carries the observed last-3F seconds (PastRun.
        last3f_seconds, written by the career / official-CSV /
        result-page ingestion), and the publish lane hands
        each runner's recent sequence in as closing_inputs
        (see closing_inputs_from_race — race-record data, not
        materials-file data, exactly like combo). The feature
        is closing_dev, the horse's own latest seconds against
        its own recent mean, so raw seconds are never compared
        across horses; integrate() z-scores the per-horse
        deviation within the race. Trial weight +0.10,
        UNVALIDATED; NK_CLOSING_TRIAL and
        NK_CLOSING_WEIGHTS_LABEL record it on every
        publication the term touches. Runners with no observed
        last-3F at all contribute nothing. The ability layer's
        own closing feature (a corner-position estimate inside
        v8) is untouched — this term is materials-only, like
        the other trials.

    horse-analysis (each horse's netkeiba data-analysis
        judgements) — wired 2026-11-19 by the same user
        instruction, after the full audit found the collection
        starting that day (horse-analysis.json: the data-analysis
        tab's per-horse 総合評価 letter grade and each section's
        suitability judgement — コース / 距離 / 産駒 / ローテ /
        枠順 / その他） with NO receptacle anywhere in the lane.
        The adapter scores the judgements (the grade and the
        section marks, each on a 0..1 scale, averaged over the
        components the collection actually saved) and applies
        ONE more z term at the trial weight +0.10, as a
        post-integrate logit adjustment: integrated_eval is a
        frozen verbatim vendor copy with no slot for this
        family, and a softmax logit shift is exactly the
        operation integrate() performs per term, so the result
        is identical to an in-formula term while the frozen
        file stays untouched. UNVALIDATED; stamped
        horse-analysis-trial-20261119 on every publication it
        touches, to be judged on forward racing only.

    course persons (the course-analysis persons tables'
        per-horse rows) — wired 2026-11-19 (nk-materials-v10)
        by the same instruction, after the audit found the
        collected jockey / trainer rows （得意な騎手・調教師，
        per entered horse) with no receptacle: each row is
        THIS race's jockey's / trainer's record at today's
        course (past-3-years window, as the page states). The
        adapter scores a record the way it scores the sire's
        course record (the mean of the win rate and the top-3
        rate, shrunk toward a generic field) and applies one
        post-integrate logit z term per person kind at the
        trial weight +0.10, by the same frozen-file reasoning
        as horse-analysis. UNVALIDATED; stamped
        course-persons-trial-20261119 on every publication
        either kind touches, to be judged on forward racing
        only. (The sire rows of the same collection feed the
        pedigree term's sireCourse fallback in the builder —
        a different landing spot for a different table.)

A race with no materials entry, or whose entry cannot produce a
single nonzero term (fewer than three horses with an index — the
z-scores need three), is returned byte-identical: the adjustment
never invents a value and never partially applies.
"""
from __future__ import annotations

import math

from ..safety.probability import distribution, marginals
from .ability import RECENCY_DECAY
from .forecast import RaceForecast, RunnerForecast, _assign_marks
from .integrated_eval import DEFAULT_WEIGHTS, integrate

# nk-materials-v8 (2026-11-19): the builder widens the speed-derived
# features' input window from the recent 3 runs to the collected 5-run
# sequence (nk_recent5) where available. Weights are unchanged from
# v7 — only the input window moved. Trial adoption per the user's
# standing instruction to put all collected data into the forecast;
# unvalidated (no historical 5-run corpus exists).
# nk-materials-v9 (2026-11-19): version bump only — weights and terms
# are identical to v8. The bump re-issues pre-race races with the
# complete materials file (pedigree / bestTime / headToHead populated)
# now that the full pedigree collection (siblings included) finished.
# nk-materials-v10 (2026-11-19): the all-wiring final form — v9 plus
# the audit-driven wiring (horse-analysis term, odds list shape,
# course-persons sire fallback, zero-coverage record) and the new
# course-persons jockey/trainer trial terms. The bump re-issues
# v9-stamped pre-race races once so the new terms reach them.
# nk-materials-v11 (2026-11-19): version bump only — weights and terms
# are identical to v10. The bump re-issues v10-stamped pre-race races
# once so the completed horse-analysis collection (all 395 horses,
# was 1 in the v10 file) reaches them through the horse_analysis term.
NK_MATERIALS_VERSION = "nk-materials-v11"
NK_WEIGHTS_LABEL = "integrated-eval-defaults-20261116"
# All-materials trial terms (v5, see the module docstring):
# bestTime / headToHead / pedigree / press at trial weights.
# mochitime's sign is negative BY DESIGN (lower time = better);
# the other three reward higher values. These weights are NOT
# validated — the label says so on every stamp they touch.
ALL_TERMS_WEIGHTS = {"mochitime": -0.10, "h2h": 0.10,
                     "pedigree": 0.10, "press": 0.10}
NK_ALL_TERMS_LABEL = (
    "all-materials-trial-20261117(mochitime-0.10/h2h+0.10/"
    "pedigree+0.10/press+0.10;unvalidated)")
NK_ALL_TERMS_TRIAL = "all-materials-trial-20261117"
# Newspaper mark points: the research tree's definition
# (new-model features.py MARK_POINTS), verbatim.
MARK_POINTS = {"◎": 5.0, "○": 4.0, "▲": 3.0, "△": 2.0, "☆": 1.0,
               "消": 0.0, "×": 0.0}
# Head-to-head shrinkage: toward the neutral ahead rate 0.5
# with the strength of 3 prior duels (the same prior strength
# integrated_eval's combo shrinkage uses).
H2H_PRIOR_DUELS = 3.0
H2H_PRIOR_RATE = 0.5
# Sire-course shrinkage: toward a generic 10-runner field's
# rates with the strength of 10 prior starts.
SIRE_PRIOR_STARTS = 10.0
SIRE_PRIOR_WIN_RATE = 0.10
SIRE_PRIOR_TOP3_RATE = 0.30
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

# Closing term (v7, 2026-11-18): TRIAL weight, UNVALIDATED. The
# input is the horse's own observed last-3F seconds from its past
# runs on the race record (see closing_inputs_from_race);
# integrated_eval's closing feature is closing_dev (own recent
# mean minus latest seconds), so a positive weight rewards a
# horse whose latest finish was faster than its own recent norm.
# Raw seconds are never compared across horses — integrate()
# z-scores the per-horse deviation within the race.
CLOSING_WEIGHT = 0.10
NK_CLOSING_WEIGHTS_LABEL = "closing-trial-20261118(w=+0.10;unvalidated)"
NK_CLOSING_TRIAL = "closing-observed-last3f"

# v6 trial families (see the module docstring). All UNVALIDATED,
# all magnitude 0.10 like the other trial terms; each family's
# label is stamped only on publications where one of its terms
# actually contributed, so an armed-but-dataless family leaves
# no trace on the stamp.
# Speed derived features: signs per integrated_eval's design
# notes (dispersion family negative, the rest positive).
SPEED_DERIVED_WEIGHTS = {
    "speed_slope": 0.10, "speed_dev": 0.10, "speed_vol": -0.10,
    "speed_sd": -0.10, "speed_overlap": -0.10, "speed_fit": 0.10,
    "speed_bias": 0.10}
SPEED_DERIVED_TERMS = tuple(SPEED_DERIVED_WEIGHTS)
NK_SPEED_DERIVED_LABEL = (
    "speed-derived-trial-20261117(slope+0.10/dev+0.10/vol-0.10/"
    "sd-0.10/overlap-0.10/fit+0.10/bias+0.10;unvalidated)")
NK_SPEED_DERIVED_TRIAL = "speed-derived-trial-20261117"
# Jockey x horse combination record, from the race record.
COMBO_WEIGHT = 0.10
NK_COMBO_LABEL = "combo-trial-20261117(w=0.10;unvalidated)"
NK_COMBO_TRIAL = "combo-trial-20261117"
# netkeiba's own judgements (form deviation / AI forecast):
# armed at trial weights; no collection data exists yet.
JUDGEMENT_WEIGHTS = {"nk_form_dev": 0.10, "nk_ai": 0.10}
NK_JUDGEMENT_LABEL = (
    "nk-judgement-trial-20261117(form-dev+0.10/ai+0.10;"
    "unvalidated)")
NK_JUDGEMENT_TRIAL = "nk-judgement-trial-20261117"
# Odds movement (drift / win-place gap): armed at trial
# weights; no collection data exists yet.
ODDS_WEIGHTS = {"odds_drift": 0.10, "odds_wp_gap": 0.10}
NK_ODDS_LABEL = (
    "odds-movement-trial-20261117(drift+0.10/wp-gap+0.10;"
    "unvalidated)")
NK_ODDS_TRIAL = "odds-movement-trial-20261117"

# Horse-analysis judgements (the netkeiba data-analysis tab's
# per-horse overall grade + section suitability marks): TRIAL
# weight, UNVALIDATED — see the module docstring. The score is
# the mean of the components the collection saved, each on a
# 0..1 scale (grade S=1.0, A=0.8, B=0.6, C=0.4, D=0.2, E=0.0;
# section marks ◎=1.0, ○=0.75, ▲=0.5, △=0.25, ×=0.0). Unknown
# symbols are ignored, never guessed.
HORSE_ANALYSIS_WEIGHT = 0.10
NK_HORSE_ANALYSIS_LABEL = (
    "horse-analysis-trial-20261119(w=+0.10;unvalidated)")
NK_HORSE_ANALYSIS_TRIAL = "horse-analysis-trial-20261119"
_HA_GRADE_POINTS = {"S": 1.0, "A": 0.8, "B": 0.6, "C": 0.4,
                    "D": 0.2, "E": 0.0}
_HA_MARK_POINTS = {"◎": 1.0, "○": 0.75, "▲": 0.5, "△": 0.25,
                   "×": 0.0}

# Course persons (the course-analysis persons tables — 得意な
# 騎手 / 得意な調教師 — as per-entered-horse rows: THIS race's
# jockey's and trainer's records at today's course): TRIAL
# weight, UNVALIDATED — see the module docstring. The score
# mirrors sire_course_score: the mean of the win rate and the
# top-3 rate, each shrunk toward a generic 10-runner field
# (0.10 / 0.30) with prior strength PERSON_PRIOR_STARTS.
# Applied like the horse-analysis term (adapter-side
# post-integrate logit shifts, one per person kind) because
# integrated_eval is frozen and has no slot for them.
COURSE_PERSONS_WEIGHT = 0.10
NK_COURSE_PERSONS_LABEL = (
    "course-persons-trial-20261119(jockey+0.10/trainer+0.10;"
    "unvalidated)")
NK_COURSE_PERSONS_TRIAL = "course-persons-trial-20261119"
PERSON_PRIOR_STARTS = 10.0
PERSON_PRIOR_WIN_RATE = 0.10
PERSON_PRIOR_TOP3_RATE = 0.30

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

    Per horse the speed columns are read as numbers; the v2
    blocks (bestTime / headToHead / pedigree) are carried as
    dicts and press (the verbatim newspaper entry) as a dict or
    string — the term helpers below read them defensively, so
    carrying an odd shape costs the horse that term, never the
    race. The v6 fields ride the same way: nkFormDev /
    nkAiScore are read as numbers, and the odds block is
    carried as a dict (its cells are read by _odds_cells).
    The horseAnalysis block (the per-horse data-analysis
    judgements) is carried as a dict the same way and read by
    horse_analysis_score. The coursePersons block (this
    race's jockey / trainer records at today's course) rides
    as a dict the same way and is read by person_course_score.
    Anything unreadable normalises to {} (no materials
    for the date) or drops the offending race/horse — a
    malformed entry must never take the lane down, and a dropped
    horse simply receives no adjustment term.
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
                for field in ("bestTime", "headToHead", "pedigree"):
                    block = values.get(field)
                    horse[field] = (block if isinstance(block, dict)
                                    else None)
                press = values.get("press")
                horse["press"] = (press if isinstance(press, (dict, str))
                                  else None)
                horse["pace"] = _parse_pace(values.get("pace"))
                horse["nkFormDev"] = _num(values.get("nkFormDev"))
                horse["nkAiScore"] = _num(values.get("nkAiScore"))
                odds_block = values.get("odds")
                horse["odds"] = (odds_block
                                 if isinstance(odds_block, dict)
                                 else None)
                ha_block = values.get("horseAnalysis")
                horse["horseAnalysis"] = (
                    ha_block if isinstance(ha_block, dict) else None)
                cp_block = values.get("coursePersons")
                horse["coursePersons"] = (
                    cp_block if isinstance(cp_block, dict) else None)
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


# --------------------------------------- all-materials terms (v5)
def best_time_seconds(best_time):
    """The bestTime block's seconds, or None. The block is the
    builder's recorded best time under today's conditions (its
    tier fallback choice travels with the value in the file)."""
    if not isinstance(best_time, dict):
        return None
    return _num(best_time.get("seconds"))


def h2h_shrunk_rate(head_to_head):
    """The head-to-head ahead rate shrunk toward the neutral
    0.5: (ahead + PRIOR*0.5) / (duels + PRIOR). None when the
    horse has no recorded duels — no evidence, no term (a
    shrunk 0.5 for every unmet horse would still z-score
    against the met horses and invent a ranking)."""
    if not isinstance(head_to_head, dict):
        return None
    duels = _num(head_to_head.get("duels"))
    ahead = _num(head_to_head.get("ahead"))
    if duels is None or ahead is None or duels <= 0:
        return None
    return (ahead + H2H_PRIOR_DUELS * H2H_PRIOR_RATE) / (
        duels + H2H_PRIOR_DUELS)


def sire_course_score(pedigree):
    """The sire's record at today's course as one score: the
    mean of the win rate and the top-3 rate, each shrunk toward
    a generic 10-runner field (0.10 / 0.30) with prior strength
    SIRE_PRIOR_STARTS. None when the pedigree block or its
    sireCourse cell is missing, or the sire has no starts on
    the table — no evidence, no term."""
    if not isinstance(pedigree, dict):
        return None
    cell = pedigree.get("sireCourse")
    if not isinstance(cell, dict):
        return None
    starts = _num(cell.get("starts"))
    wins = _num(cell.get("wins"))
    top3 = _num(cell.get("top3"))
    if starts is None or wins is None or top3 is None or starts <= 0:
        return None
    m = SIRE_PRIOR_STARTS
    win_rate = (wins + m * SIRE_PRIOR_WIN_RATE) / (starts + m)
    top3_rate = (top3 + m * SIRE_PRIOR_TOP3_RATE) / (starts + m)
    return (win_rate + top3_rate) / 2.0


def person_course_score(record):
    """One person's (jockey's / trainer's) record at today's
    course as one score: the mean of the win rate and the
    top-3 rate, each shrunk toward a generic 10-runner field
    (0.10 / 0.30) with prior strength PERSON_PRIOR_STARTS —
    the same construction as sire_course_score. None when the
    record is missing or carries no starts — no evidence, no
    term."""
    if not isinstance(record, dict):
        return None
    starts = _num(record.get("starts"))
    wins = _num(record.get("wins"))
    top3 = _num(record.get("top3"))
    if starts is None or wins is None or top3 is None or starts <= 0:
        return None
    m = PERSON_PRIOR_STARTS
    win_rate = (wins + m * PERSON_PRIOR_WIN_RATE) / (starts + m)
    top3_rate = (top3 + m * PERSON_PRIOR_TOP3_RATE) / (starts + m)
    return (win_rate + top3_rate) / 2.0


def press_points(press):
    """The newspaper marks as one number: MARK_POINTS averaged
    over every mark the collection saved for the horse. The
    verbatim entry may be a bare mark string, or a dict with a
    "mark" string and/or a "marks" mapping (source -> mark) or
    list. Unknown marks are ignored; no readable mark at all
    means None — no evidence, no term."""
    marks = []
    if isinstance(press, str):
        marks = [press]
    elif isinstance(press, dict):
        single = press.get("mark")
        if isinstance(single, str):
            marks.append(single)
        saved = press.get("marks")
        if isinstance(saved, dict):
            marks.extend(v for v in saved.values()
                         if isinstance(v, str))
        elif isinstance(saved, list):
            marks.extend(v for v in saved if isinstance(v, str))
    points = [MARK_POINTS[m] for m in marks if m in MARK_POINTS]
    if not points:
        return None
    return sum(points) / len(points)


def horse_analysis_score(block):
    """One number in [0, 1] from a horse's collected
    horse-analysis judgements (see HORSE_ANALYSIS_WEIGHT): the
    mean of the overall grade's points and each saved section
    judgement's points. None when the block carries no readable
    component — no evidence, no term."""
    if not isinstance(block, dict):
        return None
    points = []
    grade = _HA_GRADE_POINTS.get(block.get("overall"))
    if grade is not None:
        points.append(grade)
    sections = block.get("sections")
    if isinstance(sections, dict):
        for mark in sections.values():
            value = _HA_MARK_POINTS.get(mark)
            if value is not None:
                points.append(value)
    if not points:
        return None
    return sum(points) / len(points)


def _zscores(values):
    """Within-race z-scores with integrated_eval's own
    semantics (at least three values, population sd, a flat
    field scores 0.0); None stays None. A local copy because
    integrated_eval is a frozen verbatim vendor file and the
    horse-analysis term is applied by this adapter,
    post-integrate."""
    xs = [v for v in values if v is not None]
    if len(xs) < 3:
        return [None] * len(values)
    mean = sum(xs) / len(xs)
    var = sum((x - mean) ** 2 for x in xs) / len(xs)
    sd = math.sqrt(var)
    if sd < 1e-9:
        return [0.0 if v is not None else None for v in values]
    return [((v - mean) / sd) if v is not None else None
            for v in values]


# ------------------------------------------- v6 wired families
_ODDS_CELLS = (("publishWin", "publish_win_odds"),
               ("finalWin", "final_win_odds"),
               ("placeLow", "place_odds_low"),
               ("placeHigh", "place_odds_high"))


def _odds_cells(odds):
    """The odds block's cells under integrate()'s key names:
    {publish_win_odds, final_win_odds, place_odds_low,
    place_odds_high}, each a number or None. An absent or
    malformed block yields all None — no odds material, no
    odds term (the block exists in the format so a future
    collection can fill it; no current file does)."""
    if not isinstance(odds, dict):
        return {key: None for _, key in _ODDS_CELLS}
    return {key: _num(odds.get(raw)) for raw, key in _ODDS_CELLS}


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


def _obs_int(cell):
    """An Obs cell's value as an int, or None (bools and
    non-numeric values are not data)."""
    value = cell.value if cell is not None else None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return int(value)


def combo_inputs_from_race(race) -> dict:
    """{number: {"jockey": str|None, "past_rides": [...]}}
    for the race's non-scratched runners, from the race record
    itself — the input integrated_eval's combo_features reads:
    each past run as {"jockey", "finish", "field_size"} (the
    run's own jockey name, finish and field size; unknown stays
    None) plus today's jockey name. A run whose jockey is
    unknown simply never matches a NAMED today's jockey; and
    when today's jockey itself is unknown the rides are
    reported empty — an unknown pair is no pair record, never
    an everything-matches one. Nothing is imputed."""
    out: dict = {}
    for r in race.runners:
        if r.scratched:
            continue
        today = r.jockey.value if r.jockey is not None else None
        rides = []
        if today is not None:
            for run in r.past_runs:
                rides.append({
                    "jockey": (run.jockey.value
                               if run.jockey is not None else None),
                    "finish": _obs_int(run.finish),
                    "field_size": _obs_int(run.field_size),
                })
        out[r.number] = {"jockey": today, "past_rides": rides}
    return out


def closing_inputs_from_race(race) -> dict:
    """{number: [last-3F seconds, oldest -> newest]} over each
    non-scratched runner's five most recent past runs (None where
    a run carries no observed value), from the race record's
    normalized past runs. Past runs are stored newest-first; the
    integrated closing feature expects oldest -> newest. Runners
    with no observed last-3F at all are omitted."""
    out: dict = {}
    for r in race.runners:
        if r.scratched:
            continue
        recent = []
        for run in (r.past_runs or ())[:5]:
            obs = getattr(run, "last3f_seconds", None)
            value = getattr(obs, "value", None)
            recent.append(value if isinstance(value, (int, float))
                          and not isinstance(value, bool) else None)
        if any(v is not None for v in recent):
            out[r.number] = list(reversed(recent))
    return out


def apply_nk_materials(forecast: RaceForecast, entry,
                       extras_by_number: dict | None = None,
                       segment: str | None = None,
                       course_inputs: dict | None = None,
                       combo_inputs: dict | None = None,
                       closing_inputs: dict | None = None):
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

    The v5 all-materials terms (mochitime / h2h / pedigree /
    press, ALL_TERMS_WEIGHTS) are segment-independent: they
    read the entry's per-horse blocks directly. When any of
    them contributes, info["materialsTrial"] is
    "all-materials-trial-20261117" and the weights label
    carries NK_ALL_TERMS_LABEL with each weight — the trial is
    on the record wherever the stamp is read from.

    The pace term (v4, merged into v5) is likewise
    segment-independent: it contributes whenever the entry
    carries pace-forecast positions and a directional pace
    label (H / S), at the UNVALIDATED trial weight PACE_WEIGHT;
    when it contributes, info["paceTrial"] is set and the
    weights label carries NK_PACE_WEIGHTS_LABEL.

    The v6 families (see the module docstring) follow the same
    pattern. The speed derived terms ride on the speed columns
    every entry already carries, so SPEED_DERIVED_WEIGHTS are
    always in the weight set. The combo term reads
    combo_inputs (see combo_inputs_from_race — race-record
    data, not materials-file data) and its weight joins only
    when some runner actually carries past rides. The
    judgement (nk_form_dev / nk_ai) and odds-movement
    (odds_drift / odds_wp_gap) weights are armed the same way,
    but their per-horse values exist only when the materials
    file carries nkFormDev / nkAiScore / odds — no current
    file does, so today they contribute nothing and leave no
    stamp. Each family that does contribute sets its info
    marker (speedDerivedTrial / comboTrial / judgementTrial /
    oddsTrial) and appends its label to the weights string.

    The closing term (v7) follows the same pattern again: it
    reads closing_inputs (see closing_inputs_from_race — the
    runners' own observed last-3F seconds from the race
    record's past runs) and its weight joins only when some
    runner actually carries an observed value; when it
    contributes, info["closingTrial"] is NK_CLOSING_TRIAL and
    the weights label carries NK_CLOSING_WEIGHTS_LABEL.

    The horse-analysis term (2026-11-19) reads the entry's
    per-horse horseAnalysis blocks (the netkeiba data-analysis
    tab's judgements, scored by horse_analysis_score) and
    applies as a post-integrate logit shift at
    HORSE_ANALYSIS_WEIGHT when at least three runners carry a
    score and the scores differ; when it contributes,
    info["horseAnalysisTrial"] is NK_HORSE_ANALYSIS_TRIAL,
    the weights label carries NK_HORSE_ANALYSIS_LABEL, and
    "horse_analysis" joins info["terms"].

    The course-persons terms (2026-11-19, nk-materials-v10)
    follow the same pattern once per person kind: each reads
    the entry's per-horse coursePersons records (this race's
    jockey's / trainer's record at today's course, scored by
    person_course_score) and applies as a post-integrate logit
    shift at COURSE_PERSONS_WEIGHT under the same liveness
    rule; when either contributes, info["coursePersonsTrial"]
    is NK_COURSE_PERSONS_TRIAL, the weights label carries
    NK_COURSE_PERSONS_LABEL, and "course_jockey" /
    "course_trainer" join info["terms"] for the kinds that
    contributed.
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
            # v5 all-materials terms (see module docstring):
            # best time in raw seconds (integrate z-scores;
            # the negative weight carries the direction), the
            # shrunk head-to-head rate, the shrunk sire-course
            # score and the point-scored newspaper marks.
            "mochitime": best_time_seconds(mat.get("bestTime")),
            "h2h": h2h_shrunk_rate(mat.get("headToHead")),
            "pedigree_score": sire_course_score(mat.get("pedigree")),
            "press_pts": press_points(mat.get("press")),
            # AI pace-forecast position term (v4, merged into
            # v5, UNVALIDATED trial — see the module docstring).
            "pace_score": pace_score(mat.get("pace"),
                                     entry.get("paceLabel")),
            # v6 wired families (UNVALIDATED trials — see the
            # module docstring): netkeiba's own judgements and
            # the odds-movement cells ride the materials entry
            # (absent from every current file, so None today);
            # the jockey x horse combination rides the race
            # record via combo_inputs.
            "nk_form_dev": mat.get("nkFormDev"),
            "nk_ai_score": mat.get("nkAiScore"),
            **_odds_cells(mat.get("odds")),
            "jockey": ((combo_inputs or {}).get(r.number) or {}
                       ).get("jockey"),
            "past_rides": ((combo_inputs or {}).get(r.number) or {}
                           ).get("past_rides"),
            # Observed last-3F sequence from the race record's
            # past runs (closing trial, v7 — see
            # closing_inputs_from_race).
            "last3f_recent": (closing_inputs or {}).get(r.number),
            # The horse's netkeiba data-analysis judgements,
            # scored (horse-analysis trial, 2026-11-19 — see
            # the module docstring); applied below as a
            # post-integrate logit shift.
            "ha_score": horse_analysis_score(
                mat.get("horseAnalysis")),
            # This race's jockey's / trainer's records at
            # today's course, scored (course-persons trial,
            # 2026-11-19 — see the docstring above); applied
            # below as post-integrate logit shifts.
            "cp_jockey": person_course_score(
                (mat.get("coursePersons") or {}).get("jockey")),
            "cp_trainer": person_course_score(
                (mat.get("coursePersons") or {}).get("trainer")),
        }
        if course_active:
            ci = course_inputs.get(r.number) or {}
            horse["front_rate"] = ci.get("front_rate")
            horse["_frame_group"] = _frame_group(ci.get("frame"))
        horses.append(horse)
    if len(horses) < 3:
        return forecast, info
    # The v5 all-materials terms are always on trial (their
    # weights override the frozen defaults' zeros); the course
    # weights join them when the course side is live. The v6
    # families join the same way: the speed derived weights
    # (their features are computed from the speed columns every
    # entry carries) and the armed judgement / odds weights
    # (inert until a materials file carries their values); the
    # combo weight joins only when the race record actually
    # carries past rides to read.
    weights = dict(ALL_TERMS_WEIGHTS)
    weights.update(SPEED_DERIVED_WEIGHTS)
    weights.update(JUDGEMENT_WEIGHTS)
    weights.update(ODDS_WEIGHTS)
    if combo_inputs and any(
            (ci or {}).get("past_rides")
            for ci in combo_inputs.values()):
        weights["combo"] = COMBO_WEIGHT
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
            weights.update(COURSE_WEIGHTS_JRA_TRIAL)
            course_label = NK_COURSE_WEIGHTS_JRA_TRIAL_LABEL
        else:
            weights.update(COURSE_WEIGHTS_NAR)
            course_label = NK_COURSE_WEIGHTS_LABEL
    pace_label_stamp = None
    if any(h.get("pace_score") is not None for h in horses):
        weights = dict(weights) if weights else {}
        weights["pace"] = PACE_WEIGHT
        pace_label_stamp = NK_PACE_WEIGHTS_LABEL
    closing_label_stamp = None
    if any(h.get("last3f_recent") and
           any(v is not None for v in h["last3f_recent"])
           for h in horses):
        weights["closing"] = CLOSING_WEIGHT
        closing_label_stamp = NK_CLOSING_WEIGHTS_LABEL
    for h in horses:
        h.pop("_frame_group", None)
    probs, coverage, detail = integrate(horses, weights)
    # Horse-analysis term (2026-11-19 trial — see the module
    # docstring): a post-integrate logit shift by the z-scored
    # judgement score, renormalised — identical in effect to
    # an in-formula z term, with integrated_eval untouched.
    # The term is live only when at least three horses carry a
    # score and the scores actually differ (a flat field's
    # z-scores are all 0.0 and shift nothing).
    ha_scores = [h.get("ha_score") for h in horses]
    ha_z = _zscores(ha_scores)
    ha_applied = any(z is not None and z != 0.0 for z in ha_z)
    if ha_applied:
        shifted = {}
        for h, z in zip(horses, ha_z):
            p = probs[h["num"]]
            shifted[h["num"]] = (
                p * math.exp(HORSE_ANALYSIS_WEIGHT * z)
                if z is not None else p)
        total = sum(shifted.values())
        probs = {n: p / total for n, p in shifted.items()}
    coverage["horse_analysis"] = sum(
        1 for s in ha_scores if s is not None)
    # Course-persons terms (2026-11-19 trial — see the
    # docstring above): the same post-integrate logit shift,
    # once per person kind, under the same liveness rule (at
    # least three scored runners and differing scores). A kind
    # with no collected rows simply never shifts.
    cp_applied: list = []
    for kind in ("jockey", "trainer"):
        cp_scores = [h.get(f"cp_{kind}") for h in horses]
        coverage[f"course_{kind}"] = sum(
            1 for s in cp_scores if s is not None)
        cp_z = _zscores(cp_scores)
        if not any(z is not None and z != 0.0 for z in cp_z):
            continue
        shifted = {}
        for h, z in zip(horses, cp_z):
            p = probs[h["num"]]
            shifted[h["num"]] = (
                p * math.exp(COURSE_PERSONS_WEIGHT * z)
                if z is not None else p)
        total = sum(shifted.values())
        probs = {n: p / total for n, p in shifted.items()}
        cp_applied.append(kind)
    info["coverage"] = coverage
    # The weights label records every non-default weight family
    # whose terms actually contributed to THIS race — the
    # stamp-side audit trail for all the trials.
    label_parts = [NK_WEIGHTS_LABEL]
    if any(k in d["terms"] for d in detail
           for k in ("mochitime", "h2h", "pedigree", "press")):
        label_parts.append(NK_ALL_TERMS_LABEL)
        info["materialsTrial"] = NK_ALL_TERMS_TRIAL
    if course_label is not None and any(
            k in d["terms"] for d in detail
            for k in ("course_front", "course_frame")):
        label_parts.append(course_label)
        if is_jra:
            # The trial is on the record wherever the stamp is
            # read from: the weights label above, plus this
            # explicit marker the publish lane copies into the
            # nkMaterials stamp.
            info["courseTrial"] = "jra"
    if pace_label_stamp is not None and any(
            "pace" in d["terms"] for d in detail):
        label_parts.append(pace_label_stamp)
        # Same record-keeping as the course trial: the publish
        # lane copies this marker into the nkMaterials stamp so
        # the unvalidated pace trial's forward record stays
        # separable.
        info["paceTrial"] = "ai-pace-forecast"
    if closing_label_stamp is not None and any(
            "closing" in d["terms"] for d in detail):
        label_parts.append(closing_label_stamp)
        # Same record-keeping as the pace trial.
        info["closingTrial"] = NK_CLOSING_TRIAL
    # v6 families: the same record-keeping, one marker and one
    # label part per family that actually contributed a term.
    if any(k in d["terms"] for d in detail
           for k in SPEED_DERIVED_TERMS):
        label_parts.append(NK_SPEED_DERIVED_LABEL)
        info["speedDerivedTrial"] = NK_SPEED_DERIVED_TRIAL
    if any("combo" in d["terms"] for d in detail):
        label_parts.append(NK_COMBO_LABEL)
        info["comboTrial"] = NK_COMBO_TRIAL
    if any(k in d["terms"] for d in detail
           for k in ("nk_form_dev", "nk_ai")):
        label_parts.append(NK_JUDGEMENT_LABEL)
        info["judgementTrial"] = NK_JUDGEMENT_TRIAL
    if any(k in d["terms"] for d in detail
           for k in ("odds_drift", "odds_wp_gap")):
        label_parts.append(NK_ODDS_LABEL)
        info["oddsTrial"] = NK_ODDS_TRIAL
    if ha_applied:
        label_parts.append(NK_HORSE_ANALYSIS_LABEL)
        info["horseAnalysisTrial"] = NK_HORSE_ANALYSIS_TRIAL
    if cp_applied:
        label_parts.append(NK_COURSE_PERSONS_LABEL)
        info["coursePersonsTrial"] = NK_COURSE_PERSONS_TRIAL
    if len(label_parts) > 1:
        info["weights"] = "+".join(label_parts)
    if not ha_applied and not cp_applied \
            and not any(d["terms"] for d in detail):
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
    post_terms = set()
    if ha_applied:
        post_terms.add("horse_analysis")
    for kind in cp_applied:
        post_terms.add(f"course_{kind}")
    if post_terms:
        info["terms"] = sorted(set(info["terms"]) | post_terms)
    return RaceForecast(forecast.race_id, forecast.beta,
                        forecast.probability_status, tuple(runners),
                        "ok"), info
