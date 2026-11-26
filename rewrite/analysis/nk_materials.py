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

    bias pace (the same-day track bias, read from today's
        finished races and overlaid on the pace forecast) —
        wired 2026-11-19 (nk-materials-v12) by the user's
        instruction "バイアスを読んでネット競馬の展開予想に
        あわせてだせばええやん" (read the bias and issue the
        forecast matched to netkeiba's pace forecast). At
        publish time the lane reads the day's bias at this
        race's track from the races already final on the same
        card (rewrite/analysis/bias_pace.py — the bias
        DEFINITION is the 2026-11-16 validation's, unchanged:
        the front/back and inside/outside top-3 rate
        differences of the first-corner / frame groups, shrunk
        by S/(S+2) over S qualifying source races) and overlays
        it on this race's netkeiba pace-forecast positions:

            adjustment(h) = FB * frontness(h) + IO * frame(h)

        The lane hands the finished overlay in as bias_overlay
        (publish-time data, not materials-file data, exactly
        like combo / closing); the adapter applies it as ONE
        post-integrate logit shift at the trial weight cap
        BIAS_PACE_WEIGHT (+0.10) times the RAW adjustment — no
        z-scoring, because the adjustment already carries the
        shrinkage: early on a card (few source races) the bias
        is weak by construction and the term barely moves,
        and it strengthens only as the day's evidence does. A
        horse with no forecast position carries no adjustment
        and is never shifted; a card with no qualifying source
        race produces an all-zero overlay and shifts nothing.
        UNVALIDATED as a probability term (the 2026-11-16
        same-day-bias overlay validation did not pass on its
        thin corpus — the forward record is the judge);
        stamped bias-pace-trial-20261119 on every publication
        it touches, with the day's sampleRaces on the stamp.

    full-coverage terms (2026-11-23, nk-materials-v14) — wired
        by the user's instruction "全部取れて全部効いてるように
        しろ" (collect EVERYTHING and make ALL of it count),
        after the full-coverage audit found five more collected
        materials that reached the file but no term read:

        nk_best     the speed page's best index, through
            integrated_eval's own last_vs_best feature (latest
            index minus the horse's best): computed inside
            integrate() since v1 and reported in its detail,
            but no weight ever read it. The adapter applies it
            as a post-integrate logit shift (integrated_eval is
            frozen and has no weight slot the adapter may set
            for this feature alone), +0.10 rewarding a latest
            run at the horse's demonstrated peak (0 = at peak).
        siblings    the pedigree block's sibling record (count
            / total wins from the collected horse profiles),
            scored as wins per sibling shrunk toward 1.0 with
            prior strength 2 siblings. Until v14 the pedigree
            term read sireCourse only and the siblings rode
            unread. +0.10.
        press_rating  the newspaper rating （レーティング） the
            builder carries as pressRating when a collection
            saves one. No current collection saves the key, so
            the term is armed but dataless today — it lights
            the day a rating is collected, and its coverage is
            counted so the zero stays on the record. +0.10.
        pace_early  the AI pace forecast's start / corner3
            positions, as a sibling of the corner4 pace term:
            the same signed construction (sign of the pace
            label times the mean early percentile centred on
            0.5), so the early shape of the forecast counts
            alongside the late shape instead of being carried
            unread. +0.10.
        odds_forecast  netkeiba's published FORECAST win odds
            (the materials file's forecastWin — NOT the
            market's actual odds; it is never promoted to the
            actual cells), scored as -log(forecastWin) so a
            shorter forecast price reads higher. This is
            netkeiba's own expectation as a material, distinct
            from the odds-movement family, which keeps its
            actual-odds definitions. +0.10.

        All five are UNVALIDATED trial terms at +0.10, applied
        as post-integrate logit shifts under the same liveness
        rule as horse-analysis (at least three scored runners
        and differing scores), stamped
        full-coverage-trial-20261123 on every publication any
        of them touches. Their movement is measured in the
        2026-11-23 full-coverage REPORT's ablation (each family
        removed in turn over real packs; a family that does not
        move the numbers is reported as such, not as wired).

    style terms (2026-11-26, nk-materials-v15) — wired by the
        user's instruction after the morning collection began
        saving two more per-horse values from the pace-forecast
        page (the A-2 additions to pace-forecast.json's
        horses_extra) that reached the file with no term
        reading them:

        style_fit   the pace page's old-style running-style
            classification （脚質： 逃げ / 先行 / 差し / 追込） —
            the horse's own trait, read off its past races —
            scored as its agreement with the position THIS
            race's pace forecast assigns it. Trait and forecast
            are both read as a closingness in [-1, 1] (the
            trait on the four-class scale 逃げ -1, 先行 -1/3,
            差し +1/3, 追込 +1; the forecast as the mean of
            (pct - 0.5) * 2 over the phases the horse carries)
            and the score is 1 - |trait - forecast| / 2 in
            [0, 1]: 1 when the forecast lets the horse run
            exactly its own race. The existing pace terms price
            the forecast position against the pace LABEL (pace
            reads corner4, pace_early the early phases); this
            term never reads the label, so the label-driven
            pace total does not grow — what it adds is the
            trait itself, and the mismatch the position-only
            terms cannot see (a front trait forecast to be
            buried mid-field, a closer forecast to be dragged
            toward the front).
        stretch     the pace page's straight-stretch rating
            （直線の伸び： 3 = 大きく伸びる, 2 = 伸びる, 1 = 少し
            伸びる) as the horse's closing strength: the raw
            rating, z-scored at application like every
            post-integrate term. A horse with no rating is
            never shifted; the rating is the forecast's, not
            an observed last-3F (the closing term reads those),
            so the two stay separate sources.

        Both are UNVALIDATED trial terms at +0.10 — the same
        order as pace / pace_early / closing — applied as
        post-integrate logit shifts under the same liveness
        rule as horse-analysis, stamped
        style-terms-trial-20261126 on every publication either
        of them touches. Their movement over the 2026-11-26
        card is measured in the style-wiring REPORT (the v15
        terms composed onto the issued v14 packs; the
        composition is exact because the post-integrate shifts
        are renormalised exponential factors over raw scores
        that do not depend on the probabilities).

    first-corner term (2026-11-26, nk-materials-v16) — the
        standing course-geometry records' first-corner
        distance (スタートから最初のコーナーまでの距離),
        collected for 154 courses and published on the pace
        block since 2026-11-25, gains the term that reads
        it. The builder joins the record for the race's own
        (track, surface, distance) onto the materials entry
        as firstCornerMeters — the paceLabel route, a
        race-level scalar riding the entry — and the term
        prices the COURSE SHAPE against each horse's
        forecast early frontness:

        score = course_factor(D) x early_frontness(horse)

        course_factor maps the ABSOLUTE distance D onto
        [-1, 1] around the standing records' median (301.5m
        over the 154 records of 2026-11-26): 0 at 300m,
        saturating at 0m (a turn at the start — the hardest
        possible scramble for position) and at 600m (the
        field long settled — no further gain). The absolute
        distance is the scale, never the share of the race
        distance: the scramble is over the dash itself, and
        the same 300m dash costs the same whether the race
        is 1400m or 2000m. early_frontness is the negated
        closingness of the horse's early (start / corner3)
        pace-forecast positions — the same early phases
        pace_early reads, on the same [-1, 1] scale style_fit
        uses (+1 = forecast to run at the very front early).

        The direction is the mineta reading the records were
        collected for: a short run to the first corner makes
        the front runners spend for their position (a front
        horse scores down, a closer up — the field settles
        early behind them); a long run lets the front take
        position cheaply (the signs reverse). This is an
        interaction only — the distance's main effect is not
        priced, and the style trait is never read (style_fit
        prices the trait against the forecast; this term
        prices the course against the forecast).

        The term is an UNVALIDATED trial at +0.10, applied
        as a post-integrate logit shift — but deliberately
        NOT z-scored, on the bias_pace precedent: the raw
        score already carries its own strength, because the
        course factor is 0 at the median course. A z-scored
        form would reduce the term to flipping the frontness
        ranking at full trial strength on every non-median
        course, however ordinary; here the shift is weak
        exactly when the course is. Liveness follows
        bias_pace (at least three scored runners, differing
        scores). Stamped first-corner-trial-20261126 on
        every publication it touches. A course with no
        record (the geometry file carries none for it) and a
        horse with no early forecast position are never
        shifted — a distance is never estimated. The records
        carry no inner/outer-course distinction
        （内回り/外回り), so a course whose variants differ
        in the run to the first corner is read at its
        recorded single value; that is a known limit of the
        source, recorded here.

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
from .integrated_eval import DEFAULT_WEIGHTS, comment_score, integrate

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
# nk-materials-v12 (2026-11-19): the same-day bias read joins as
# the bias_pace term (see the module docstring): the publish lane
# computes the day's bias from the card's already-final races
# (rewrite/analysis/bias_pace.py) and overlays it on the race's
# pace forecast; the adapter applies it as a post-integrate logit
# shift at the +0.10 cap times the (already strength-shrunk)
# adjustment. The bump re-issues v11-stamped pre-race races once
# so the term can reach them; a race whose card has no qualifying
# source race yet recomputes with the term inert.
# nk-materials-v13 (2026-11-21): no materials change — the bump
# carries the extended-mark rule (rewrite/analysis/forecast.py:
# win-probability ranks 6-8 at >= 2% additionally receive 注, 穴,
# 伏, user-directed after the mark-coverage verification) into
# still-pre-post races: every v12-stamped race with a materials
# entry re-issues exactly once through the full rebuild, which
# re-derives the marks from the adjusted probabilities.
# nk-materials-v14 (2026-11-23): the full-coverage wiring (see
# the module docstring): five collected-but-unread materials
# gain trial terms (nk_best / siblings / press_rating /
# pace_early / odds_forecast), and the builder's
# details-independent joins restore pedigree / sireCourse /
# courseJockey / courseTrainer on days with no race-details
# input. The bump re-issues v13-stamped pre-race races once so
# the new terms and the restored blocks reach them.
# nk-materials-v15 (2026-11-26): the style terms (see the
# module docstring): the pace forecast page's per-horse
# running-style classification and straight-stretch rating —
# saved by the collection from 2026-11-26 and carried by the
# builder as styleClass / stretch — gain trial terms
# (style_fit / stretch) as post-integrate logit shifts. The
# bump re-issues v14-stamped pre-race races once so the new
# terms reach them; both families also join the materials
# fingerprint, so a race whose style material arrives after
# first publication re-qualifies like any other growth.
# nk-materials-v16 (2026-11-26): the first-corner term (see
# the module docstring): the standing course-geometry
# records' first-corner distance — carried by the builder
# (v14) on the materials entry as firstCornerMeters — gains
# a trial term (first_corner) as a post-integrate logit
# shift at the raw score (no z-scoring; the bias-pace
# precedent). The bump re-issues v15-stamped pre-race races
# once so the term reaches them; the family also joins the
# materials fingerprint, so a race whose course gains a
# geometry record after first publication re-qualifies.
NK_MATERIALS_VERSION = "nk-materials-v16"
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

# Same-day bias pace term (2026-11-19, nk-materials-v12):
# TRIAL weight cap, UNVALIDATED — see the module docstring.
# The publish lane computes the overlay with
# rewrite/analysis/bias_pace.py (the day's bias, read from the
# card's already-final races, overlaid on the netkeiba pace
# forecast) and hands it in as bias_overlay; the adapter
# applies each horse's adjustment as a post-integrate logit
# shift at BIAS_PACE_WEIGHT times the raw adjustment. The
# adjustment already carries the bias module's S/(S+2)
# shrinkage, so the effective weight weakens automatically
# when the day has produced few source races — this weight is
# a cap, not a constant.
BIAS_PACE_WEIGHT = 0.10
NK_BIAS_PACE_LABEL = (
    "bias-pace-trial-20261119(w-cap=+0.10;strength-shrunk;"
    "unvalidated)")
NK_BIAS_PACE_TRIAL = "bias-pace-trial-20261119"

# Full-coverage terms (2026-11-23, nk-materials-v14): TRIAL
# weights, UNVALIDATED — see the module docstring. Five
# collected materials that reached the materials file unread
# (nk_best's last_vs_best, the pedigree siblings, the
# newspaper rating, the pace forecast's early phases, and
# netkeiba's forecast win odds) join as post-integrate logit
# shifts at +0.10 each, under the horse-analysis liveness rule.
FULL_COVERAGE_WEIGHT = 0.10
NK_FULL_COVERAGE_LABEL = (
    "full-coverage-trial-20261123(nk-best+0.10/siblings+0.10/"
    "press-rating+0.10/pace-early+0.10/odds-forecast+0.10;"
    "unvalidated)")
NK_FULL_COVERAGE_TRIAL = "full-coverage-trial-20261123"
FULL_COVERAGE_TERMS = ("nk_best", "siblings", "press_rating",
                       "pace_early", "odds_forecast")
# Siblings shrinkage: wins per sibling toward a generic 1.0
# wins per sibling, with the strength of 2 prior siblings.
SIBLING_PRIOR_COUNT = 2.0
SIBLING_PRIOR_WINS_PER = 1.0

# Style terms (2026-11-26, nk-materials-v15): TRIAL weight,
# UNVALIDATED — see the module docstring. The pace forecast
# page's per-horse style classification and stretch rating,
# applied as post-integrate logit shifts at the same +0.10
# order as the other pace-family trials (pace / pace_early /
# closing). style_fit deliberately never reads the pace
# label — pace and pace_early already price position x label
# — so the family's label-driven total does not grow; its
# per-horse inputs are the trait and the rating.
STYLE_WEIGHT = 0.10
NK_STYLE_LABEL = (
    "style-terms-trial-20261126(style-fit+0.10/stretch+0.10;"
    "unvalidated)")
NK_STYLE_TRIAL = "style-terms-trial-20261126"
STYLE_TERMS = ("style_fit", "stretch")
# The style classification as a closingness in [-1, 1]: the
# four classes evenly spaced, the front trait (逃げ) at -1
# and the deepest closer (追込) at +1 — the same scale
# pace_score puts a forecast position on ((pct - 0.5) * 2),
# so trait and forecast compare directly in style_fit_score.
_STYLE_CLOSINGNESS = {"逃げ": -1.0, "先行": -1.0 / 3.0,
                      "差し": 1.0 / 3.0, "追込": 1.0}

# First-corner term (2026-11-26, nk-materials-v16): TRIAL
# weight, UNVALIDATED — see the module docstring. The
# standing course-geometry record's first-corner distance,
# carried by the builder on the materials entry as
# firstCornerMeters, priced as an interaction with the
# horse's forecast early frontness. Deliberately NOT
# z-scored: like bias_pace, the raw score already carries
# its own strength — the course factor is 0 at the standing
# records' median distance, so an ordinary course shifts
# almost nothing however the field's frontness spreads, and
# only a genuinely short or long run to the first corner
# moves the numbers.
FIRST_CORNER_WEIGHT = 0.10
NK_FIRST_CORNER_LABEL = (
    "first-corner-trial-20261126(w=+0.10;unvalidated)")
NK_FIRST_CORNER_TRIAL = "first-corner-trial-20261126"
FIRST_CORNER_TERMS = ("first_corner",)
# The course factor's centre and scale in metres: the
# centre is the median first-corner distance of the
# standing geometry records (301.5m over the 154 records
# of 2026-11-26), and the scale makes the factor saturate
# at a 0m run (a turn at the start) and a 600m run (the
# field long settled).
FIRST_CORNER_CENTER_M = 300.0
FIRST_CORNER_SCALE_M = 300.0

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


def nk_best_score(horse):
    """last_vs_best for one parsed materials horse: the latest
    speed index (the last non-null entry of nk_recent) minus
    the horse's own best index (nk_best) — integrated_eval's
    own trend feature, which its frozen weights never read.
    0 means the latest run equals the horse's demonstrated
    peak; negative is the headroom below it. None when either
    side is missing — no evidence, no term."""
    if not isinstance(horse, dict):
        return None
    best = _num(horse.get("nk_best"))
    recent = horse.get("nk_recent")
    if best is None or not isinstance(recent, list):
        return None
    pts = [v for v in recent if v is not None]
    if not pts:
        return None
    return pts[-1] - best


def siblings_score(pedigree):
    """The pedigree block's sibling record as one score: wins
    per sibling, shrunk toward SIBLING_PRIOR_WINS_PER with
    prior strength SIBLING_PRIOR_COUNT siblings, so a single
    prolific sibling does not read as a proven family. None
    when the block or the siblings cell is missing or carries
    no siblings — no evidence, no term."""
    if not isinstance(pedigree, dict):
        return None
    sib = pedigree.get("siblings")
    if not isinstance(sib, dict):
        return None
    count = _num(sib.get("count"))
    wins = _num(sib.get("wins"))
    if count is None or wins is None or count <= 0:
        return None
    return (wins + SIBLING_PRIOR_COUNT * SIBLING_PRIOR_WINS_PER) / (
        count + SIBLING_PRIOR_COUNT)


def pace_early_score(pace, label):
    """The pace term's early-phase sibling (see the module
    docstring): sign(label) * (mean start / corner3 percentile
    - 0.5) * 2, over the early phases the horse carries. None
    when the label carries no direction or the horse has no
    early forecast position."""
    sign = _PACE_SIGNS.get(label) if isinstance(label, str) else None
    if sign is None or not isinstance(pace, dict):
        return None
    pcts = []
    for phase in ("start", "corner3"):
        cell = pace.get(phase)
        if not isinstance(cell, dict):
            continue
        pct = _num(cell.get("pct"))
        if pct is not None:
            pcts.append(pct)
    if not pcts:
        return None
    return sign * (sum(pcts) / len(pcts) - 0.5) * 2.0


def odds_forecast_score(odds):
    """netkeiba's published FORECAST win odds as one score:
    -log(forecastWin), so a shorter forecast price reads
    higher. This is the forecast line under its own name — it
    is NOT the market's actual odds and never feeds the
    odds-movement features. None when the block carries no
    forecast line (or a line of 1.0 or less, which is not an
    odds value) — no evidence, no term."""
    if not isinstance(odds, dict):
        return None
    fw = _num(odds.get("forecastWin"))
    if fw is None or fw <= 1.0:
        return None
    return -math.log(fw)


def style_fit_score(style_class, pace):
    """The style term's raw score in [0, 1] (see the module
    docstring): the agreement between the horse's running-
    style trait and its pace-forecast positions, both read as
    a closingness in [-1, 1] — 1 when the forecast puts the
    horse exactly where its trait runs, 0 when it puts it at
    the opposite end. The pace label is never read (pace /
    pace_early price position x label; this term prices the
    trait against the position). None when the horse carries
    no readable style class or no forecast position — no
    evidence, no term."""
    if not isinstance(style_class, str) \
            or not isinstance(pace, dict):
        return None
    trait = _STYLE_CLOSINGNESS.get(style_class)
    if trait is None:
        return None
    vals = []
    for phase in _PACE_PHASES:
        cell = pace.get(phase)
        if not isinstance(cell, dict):
            continue
        pct = _num(cell.get("pct"))
        if pct is not None:
            vals.append((pct - 0.5) * 2.0)
    if not vals:
        return None
    forecast = sum(vals) / len(vals)
    return 1.0 - abs(trait - forecast) / 2.0


def stretch_score(stretch):
    """The stretch term's raw score: the pace forecast's
    straight-stretch rating (3 = 大きく伸びる, 2 = 伸びる,
    1 = 少し伸びる) as a number. None when the horse carries
    no rating in [1, 3] — no evidence, no term. The rating is
    z-scored at application, so the raw scale only needs its
    order; it is the forecast's rating, never an observed
    last-3F (the closing term reads those)."""
    value = _num(stretch)
    if value is None or value < 1 or value > 3:
        return None
    return float(value)


def first_corner_factor(first_corner_meters):
    """The course factor in [-1, 1] for one first-corner
    distance (see the module docstring): +1 when the run to
    the first corner is long (the front takes position
    without spending), -1 when it is short (the scramble
    costs the front), 0 at the standing records' median
    distance. The ABSOLUTE distance is the scale, never the
    share of the race distance — the scramble is over the
    dash itself. None when the course carries no recorded
    distance — no record, no term; a distance is never
    estimated."""
    d = _num(first_corner_meters)
    if d is None or d <= 0:
        return None
    return max(-1.0, min(1.0, (
        d - FIRST_CORNER_CENTER_M) / FIRST_CORNER_SCALE_M))


def first_corner_score(first_corner_meters, pace):
    """The first-corner term's raw score in [-1, 1] (see the
    module docstring): the course factor times the horse's
    forecast early frontness — the negated closingness of
    its early (start / corner3) pace-forecast positions, the
    same early phases pace_early_score reads, on the same
    [-1, 1] scale style_fit uses (+1 = forecast to run at
    the very front early). A front horse on a short-run
    course scores down (it pays for its position); the same
    horse on a long-run course scores up; a closer's signs
    reverse. The style trait is never read — style_fit
    prices the trait; this term prices the course shape
    against the forecast itself. None when the course
    carries no recorded distance or the horse carries no
    early forecast position — no evidence, no term."""
    factor = first_corner_factor(first_corner_meters)
    if factor is None or not isinstance(pace, dict):
        return None
    pcts = []
    for phase in ("start", "corner3"):
        cell = pace.get(phase)
        if not isinstance(cell, dict):
            continue
        pct = _num(cell.get("pct"))
        if pct is not None:
            pcts.append(pct)
    if not pcts:
        return None
    frontness = -((sum(pcts) / len(pcts) - 0.5) * 2.0)
    return factor * frontness


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
    The v15 style fields ride the same way: styleClass (the
    pace page's running-style classification) is carried only
    when it is one of the four labels, and stretch (the pace
    page's straight-stretch rating) only as a number in
    [1, 3]; they are read by style_fit_score / stretch_score.
    The entry-level firstCornerMeters (the standing
    course-geometry record's run to the first corner for
    this race's course, joined by the builder) is carried
    as a positive number or None and read by
    first_corner_score.
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
                # 2026-11-21 fix2 (B6/B7): the comment / grade
                # inputs integrate() reads. Until now the parser
                # never carried them, so even a builder file that
                # had them would have dropped both here — the two
                # heaviest integrated terms (comment 0.25, grade
                # 0.20) were dark at two independent points.
                comment_text = values.get("comment_text")
                horse["comment_text"] = (
                    comment_text.strip()
                    if isinstance(comment_text, str)
                    and comment_text.strip() else None)
                grade = values.get("grade")
                horse["grade"] = (
                    grade.strip()
                    if isinstance(grade, str)
                    and grade.strip() in ("A", "B", "C", "D") else None)
                stable = values.get("stableComment")
                horse["stableComment"] = (
                    stable.strip()
                    if isinstance(stable, str) and stable.strip()
                    else None)
                horse["pressRating"] = _num(values.get("pressRating"))
                horse["pace"] = _parse_pace(values.get("pace"))
                # v15 style fields (2026-11-26): the pace
                # page's style classification and stretch
                # rating, carried defensively — an unknown
                # label or an out-of-range rating is no
                # material, never a guessed one.
                style = values.get("styleClass")
                horse["styleClass"] = (
                    style if isinstance(style, str)
                    and style in _STYLE_CLOSINGNESS else None)
                stretch = _num(values.get("stretch"))
                horse["stretch"] = (
                    stretch if stretch is not None
                    and 1 <= stretch <= 3 else None)
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
        fc_meters = _num(entry.get("firstCornerMeters"))
        out[str(race_id)] = {
            "netkeibaRaceId": entry.get("netkeibaRaceId"),
            "horses": horses,
            "courseAnalysis": course if isinstance(course, dict) else None,
            "paceLabel": label if isinstance(label, str) else None,
            "firstCornerMeters": (
                fc_meters if fc_meters is not None and fc_meters > 0
                else None),
        }
    return out


def speed_coverage(entry) -> int:
    """Horses in the entry carrying the representative index
    (nk_avg5) — the coverage the speed term stands on."""
    if not isinstance(entry, dict):
        return 0
    return sum(1 for h in (entry.get("horses") or {}).values()
               if isinstance(h, dict) and h.get("nk_avg5") is not None)


def materials_fingerprint(entry) -> dict:
    """Per-family counts of horses carrying a usable value in
    one parsed materials entry, keyed by the integrate()
    coverage names (plus the entry-level course_analysis flag).

    This is the content state of the materials file for one
    race, in the exact units the adjustment consumes: a family
    count can only grow when newly collected material lands
    (the morning rebuild lighting bestTime / headToHead / the
    odds block after the evening file had shipped without
    them). The publish lane stamps the fingerprint of the
    entry it applied and re-qualifies a frozen race when the
    current entry's fingerprint has outgrown the stamped one
    (see scripts/arvexq_rewrite_publish.py,
    _nk_materials_upgrade_info) — the stamp keys on WHAT was
    applied, not only on the adjustment definition's version,
    so material that arrives after first publication still
    reaches a pre-post race. Counts use the same per-family
    readers apply_nk_materials uses, so the fingerprint never
    claims material the adjustment could not read."""
    counts = {
        "speed": 0, "mochitime": 0, "h2h": 0, "pedigree": 0,
        "press": 0, "pace": 0, "nk_form_dev": 0, "nk_ai": 0,
        "odds_drift": 0, "odds_wp_gap": 0, "horse_analysis": 0,
        "course_jockey": 0, "course_trainer": 0,
        "course_analysis": 0,
        # 2026-11-21 fix2 (B6/B7): the comment / grade families
        # join the fingerprint so a race whose comments or grades
        # arrive after first publication re-qualifies like any
        # other material growth.
        "comment": 0, "grade": 0,
        # 2026-11-23 (v14): the full-coverage families join the
        # fingerprint on the same rule — material growth in any
        # of them re-qualifies a frozen race.
        "nk_best": 0, "siblings": 0, "press_rating": 0,
        "pace_early": 0, "odds_forecast": 0,
        # 2026-11-26 (v15): the style families join the
        # fingerprint on the same rule.
        "style_fit": 0, "stretch": 0,
        "first_corner": 0,
    }
    if not isinstance(entry, dict):
        return counts
    if isinstance(entry.get("courseAnalysis"), dict) \
            and entry.get("courseAnalysis"):
        counts["course_analysis"] = 1
    pace_label = entry.get("paceLabel")
    first_corner_meters = entry.get("firstCornerMeters")
    for horse in (entry.get("horses") or {}).values():
        if not isinstance(horse, dict):
            continue
        if horse.get("nk_avg5") is not None:
            counts["speed"] += 1
        if best_time_seconds(horse.get("bestTime")) is not None:
            counts["mochitime"] += 1
        if h2h_shrunk_rate(horse.get("headToHead")) is not None:
            counts["h2h"] += 1
        if sire_course_score(horse.get("pedigree")) is not None:
            counts["pedigree"] += 1
        if press_points(horse.get("press")) is not None:
            counts["press"] += 1
        if pace_score(horse.get("pace"), pace_label) is not None:
            counts["pace"] += 1
        if comment_score(horse.get("comment_text"))[0] is not None:
            counts["comment"] += 1
        if horse.get("grade") in ("A", "B", "C"):
            counts["grade"] += 1
        if horse.get("nkFormDev") is not None:
            counts["nk_form_dev"] += 1
        if horse.get("nkAiScore") is not None:
            counts["nk_ai"] += 1
        cells = _odds_cells(horse.get("odds"))
        if cells.get("publish_win_odds") and cells.get("final_win_odds"):
            counts["odds_drift"] += 1
        if cells.get("final_win_odds") \
                and cells.get("place_odds_low") \
                and cells.get("place_odds_high"):
            counts["odds_wp_gap"] += 1
        if horse_analysis_score(horse.get("horseAnalysis")) is not None:
            counts["horse_analysis"] += 1
        persons = horse.get("coursePersons") or {}
        if person_course_score(persons.get("jockey")) is not None:
            counts["course_jockey"] += 1
        if person_course_score(persons.get("trainer")) is not None:
            counts["course_trainer"] += 1
        if nk_best_score(horse) is not None:
            counts["nk_best"] += 1
        if siblings_score(horse.get("pedigree")) is not None:
            counts["siblings"] += 1
        if horse.get("pressRating") is not None:
            counts["press_rating"] += 1
        if pace_early_score(horse.get("pace"), pace_label) is not None:
            counts["pace_early"] += 1
        if odds_forecast_score(horse.get("odds")) is not None:
            counts["odds_forecast"] += 1
        if style_fit_score(horse.get("styleClass"),
                           horse.get("pace")) is not None:
            counts["style_fit"] += 1
        if horse.get("stretch") is not None:
            counts["stretch"] += 1
        if first_corner_score(first_corner_meters,
                              horse.get("pace")) is not None:
            counts["first_corner"] += 1
    return counts


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


# The local (NAR) course-analysis pages aggregate the frame
# table into three zones instead of one row per frame number:
# the rows are labelled 内 / 中 / 外 (the JRA pages carry one
# "N枠" row per frame). The zones are the page's own grouping
# and map onto the validation's frame groups by name — the
# per-horse side keeps assigning groups by frame number
# (_frame_group), unchanged.
_FRAME_ZONE_LABELS = {"内": "inner", "中": "mid", "外": "outer"}


def _frame_group_for_label(label: str):
    """The frame group a frame-table row belongs to: a zone
    label (内/中/外) maps by name; any other label is read as a
    frame number ("1枠", "1", ...) and grouped by number.
    None when the label carries neither — the row is skipped,
    never guessed."""
    zone = _FRAME_ZONE_LABELS.get(label)
    if zone is not None:
        return zone
    return _frame_group(_frame_number(label))


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
                group = _frame_group_for_label(label)
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
                       closing_inputs: dict | None = None,
                       bias_overlay: dict | None = None):
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

    Jumps races (segment "jumps", 2026-11-21) count as JRA for
    the course terms — they are JRA races and the collection
    carries their courseAnalysis like any other JRA race — but
    the trial marker is stamped "jra-jumps" so the jump
    record stays separable from the flat one. Jumps races have
    no v8/v9b lane (no fitted candidate exists for the
    segment), so the publish lane applies this adjustment to
    their v1 probability vector; every segment-independent
    family below applies exactly as on the v9b lane.

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

    The style terms (2026-11-26, nk-materials-v15) follow the
    same pattern once per term: style_fit reads the entry's
    per-horse styleClass (the pace page's running-style
    classification) against the horse's parsed pace positions
    (style_fit_score — the trait/forecast agreement, never
    the pace label), and stretch reads the entry's per-horse
    stretch rating (stretch_score); each applies as a
    post-integrate logit shift at STYLE_WEIGHT under the same
    liveness rule. When either contributes, info["styleTrial"]
    is NK_STYLE_TRIAL, the weights label carries
    NK_STYLE_LABEL, and "style_fit" / "stretch" join
    info["terms"] for the terms that contributed.

    The first-corner term (2026-11-26, nk-materials-v16)
    follows the bias-pace pattern instead: it reads the
    entry's firstCornerMeters (the standing course-geometry
    record for this race's course, joined by the builder)
    against each horse's parsed pace positions
    (first_corner_score — the course factor times the
    forecast early frontness) and applies as a post-integrate
    logit shift at FIRST_CORNER_WEIGHT times the RAW score —
    no z-scoring, because the course factor already carries
    the course's extremity (0 at the median course). When it
    contributes, info["firstCornerTrial"] is
    NK_FIRST_CORNER_TRIAL, the weights label carries
    NK_FIRST_CORNER_LABEL, and "first_corner" joins
    info["terms"].

    The bias-pace term (2026-11-19, nk-materials-v12) reads
    bias_overlay — the publish lane's same-day bias overlay
    (rewrite/analysis/bias_pace.py's overlay_bias_on_pace
    output over this race's materials pace positions; see the
    module docstring) — and applies each horse's adjustment
    as a post-integrate logit shift at BIAS_PACE_WEIGHT times
    the raw adjustment when at least three runners carry one
    and the adjustments differ. When it contributes,
    info["biasPaceTrial"] is NK_BIAS_PACE_TRIAL, the weights
    label carries NK_BIAS_PACE_LABEL and "bias_pace" joins
    info["terms"]. Whenever an overlay was handed in,
    info["biasPace"] records the day's bias read (available /
    frontBack / insideOutside / sampleRaces / strength)
    whether or not the term itself shifted anything, so the
    lane can stamp the read and its sample size.
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
    is_jra = segment in JRA_SEGMENTS or segment == "jumps"
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
            # Full-coverage families (v14, 2026-11-23 — see the
            # module docstring): the raw blocks the new terms
            # read, scored below as post-integrate logit shifts.
            # nk_best_score reads this dict's own nk_recent /
            # nk_best keys, already carried above for integrate().
            "pedigree_block": mat.get("pedigree"),
            "press_rating": mat.get("pressRating"),
            "pace_block": mat.get("pace"),
            "odds_block": mat.get("odds"),
            # Style families (v15, 2026-11-26 — see the module
            # docstring): the pace page's style classification
            # and stretch rating, scored below as post-
            # integrate logit shifts. style_fit reads the
            # parsed pace block already carried as pace_block.
            "style_class": mat.get("styleClass"),
            "stretch": mat.get("stretch"),
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
    # Full-coverage terms (2026-11-23 trial, nk-materials-v14
    # — see the module docstring): the same post-integrate
    # logit shift, once per family, under the same liveness
    # rule (at least three scored runners and differing
    # scores). A family whose material a day does not carry
    # (press_rating until a collection saves ratings) simply
    # never shifts, and its coverage count below stays on the
    # record at 0.
    fc_scores = {
        "nk_best": [nk_best_score(h) for h in horses],
        "siblings": [siblings_score(h.get("pedigree_block"))
                     for h in horses],
        "press_rating": [h.get("press_rating") for h in horses],
        "pace_early": [pace_early_score(
            h.get("pace_block"), entry.get("paceLabel"))
            for h in horses],
        "odds_forecast": [odds_forecast_score(h.get("odds_block"))
                          for h in horses],
    }
    fc_applied: list = []
    for term_name in FULL_COVERAGE_TERMS:
        scores = fc_scores[term_name]
        coverage[term_name] = sum(
            1 for s in scores if s is not None)
        fc_z = _zscores(scores)
        if not any(z is not None and z != 0.0 for z in fc_z):
            continue
        shifted = {}
        for h, z in zip(horses, fc_z):
            p = probs[h["num"]]
            shifted[h["num"]] = (
                p * math.exp(FULL_COVERAGE_WEIGHT * z)
                if z is not None else p)
        total = sum(shifted.values())
        probs = {n: p / total for n, p in shifted.items()}
        fc_applied.append(term_name)
    # Style terms (2026-11-26 trial, nk-materials-v15 — see
    # the module docstring): the same post-integrate logit
    # shift, once per term, under the same liveness rule (at
    # least three scored runners and differing scores). A
    # horse with no style class or no stretch rating is never
    # shifted by that term; a race whose pace entry carries
    # neither simply never shifts.
    st_scores = {
        "style_fit": [style_fit_score(
            h.get("style_class"), h.get("pace_block"))
            for h in horses],
        "stretch": [stretch_score(h.get("stretch"))
                    for h in horses],
    }
    st_applied: list = []
    for term_name in STYLE_TERMS:
        scores = st_scores[term_name]
        coverage[term_name] = sum(
            1 for s in scores if s is not None)
        st_z = _zscores(scores)
        if not any(z is not None and z != 0.0 for z in st_z):
            continue
        shifted = {}
        for h, z in zip(horses, st_z):
            p = probs[h["num"]]
            shifted[h["num"]] = (
                p * math.exp(STYLE_WEIGHT * z)
                if z is not None else p)
        total = sum(shifted.values())
        probs = {n: p / total for n, p in shifted.items()}
        st_applied.append(term_name)
    # First-corner term (2026-11-26 trial, nk-materials-v16
    # — see the module docstring): the course shape (the
    # recorded run to the first corner) against each horse's
    # forecast early frontness, applied as a post-integrate
    # logit shift at FIRST_CORNER_WEIGHT times the RAW score
    # — deliberately no z-scoring, the bias-pace precedent:
    # the course factor is 0 at the standing records' median
    # distance, so the term is weak exactly when the course
    # is ordinary. Live only when at least three runners
    # carry a score and the scores differ. A race whose
    # course has no geometry record, or a horse with no
    # early forecast position, is never shifted.
    first_corner_values = [first_corner_score(
        entry.get("firstCornerMeters"), h.get("pace_block"))
        for h in horses]
    coverage["first_corner"] = sum(
        1 for s in first_corner_values if s is not None)
    first_corner_present = [v for v in first_corner_values
                            if v is not None]
    first_corner_applied = (
        len(first_corner_present) >= 3
        and max(first_corner_present) != min(first_corner_present))
    if first_corner_applied:
        shifted = {}
        for h, v in zip(horses, first_corner_values):
            p = probs[h["num"]]
            shifted[h["num"]] = (
                p * math.exp(FIRST_CORNER_WEIGHT * v)
                if v is not None else p)
        total = sum(shifted.values())
        probs = {n: p / total for n, p in shifted.items()}
    # Same-day bias pace term (2026-11-19 trial — see the
    # module docstring): the publish lane's overlay of the
    # day's bias read on this race's pace forecast, applied
    # as a post-integrate logit shift at BIAS_PACE_WEIGHT
    # times each horse's RAW adjustment. The adjustment
    # already carries the bias module's S/(S+2) shrinkage,
    # so there is deliberately no z-scoring: the term is
    # weak exactly when the day's evidence is. Live only
    # when at least three runners carry an adjustment and
    # the adjustments differ — a card with no qualifying
    # source race yields an all-zero overlay (max == min)
    # and shifts nothing, and a horse with no forecast
    # position carries no adjustment and is never shifted.
    bp_values: list = [None] * len(horses)
    if isinstance(bias_overlay, dict):
        bp_horses = bias_overlay.get("horses")
        if isinstance(bp_horses, dict):
            for i, h in enumerate(horses):
                cell = bp_horses.get(h["num"])
                if cell is None:
                    cell = bp_horses.get(str(h["num"]))
                if isinstance(cell, dict):
                    bp_values[i] = _num(cell.get("adjustment"))
        bias_block = bias_overlay.get("bias")
        bias_block = bias_block if isinstance(bias_block, dict) else {}
        info["biasPace"] = {
            "available": bool(bias_overlay.get("available")),
            "frontBack": bias_block.get("frontBack"),
            "insideOutside": bias_block.get("insideOutside"),
            "sampleRaces": bias_block.get("sampleRaces", 0),
            "strength": bias_block.get("strength", 0.0),
        }
    coverage["bias_pace"] = sum(
        1 for v in bp_values if v is not None)
    bp_present = [v for v in bp_values if v is not None]
    bp_applied = (len(bp_present) >= 3
                  and max(bp_present) != min(bp_present))
    if bp_applied:
        shifted = {}
        for h, v in zip(horses, bp_values):
            p = probs[h["num"]]
            shifted[h["num"]] = (
                p * math.exp(BIAS_PACE_WEIGHT * v)
                if v is not None else p)
        total = sum(shifted.values())
        probs = {n: p / total for n, p in shifted.items()}
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
            # nkMaterials stamp. Jumps races carry their own
            # marker so their trial record stays separable.
            info["courseTrial"] = (
                "jra-jumps" if segment == "jumps" else "jra")
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
    if fc_applied:
        label_parts.append(NK_FULL_COVERAGE_LABEL)
        info["fullCoverageTrial"] = NK_FULL_COVERAGE_TRIAL
        info["fullCoverageTerms"] = fc_applied
    if st_applied:
        label_parts.append(NK_STYLE_LABEL)
        info["styleTrial"] = NK_STYLE_TRIAL
        info["styleTerms"] = st_applied
    if first_corner_applied:
        label_parts.append(NK_FIRST_CORNER_LABEL)
        info["firstCornerTrial"] = NK_FIRST_CORNER_TRIAL
    if bp_applied:
        label_parts.append(NK_BIAS_PACE_LABEL)
        info["biasPaceTrial"] = NK_BIAS_PACE_TRIAL
    if len(label_parts) > 1:
        info["weights"] = "+".join(label_parts)
    if not ha_applied and not cp_applied and not bp_applied \
            and not fc_applied and not st_applied \
            and not first_corner_applied \
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
    post_terms.update(fc_applied)
    post_terms.update(st_applied)
    if first_corner_applied:
        post_terms.add("first_corner")
    if bp_applied:
        post_terms.add("bias_pace")
    if post_terms:
        info["terms"] = sorted(set(info["terms"]) | post_terms)
    return RaceForecast(forecast.race_id, forecast.beta,
                        forecast.probability_status, tuple(runners),
                        "ok"), info
