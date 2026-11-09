# ARVEXQ Master 18-factor model — 2026-11-09

## Intent and release boundary

The user-supplied 18-section specification is implemented as a **pre-off
research candidate**, evaluated alongside the existing production v9b /
R24 lane. It does **not** replace v9b marks or R24 tickets before it
beats the incumbent on unseen, frozen races. There are no claimed gains
in hit rate or ROI from this change.

The publisher invokes `master_candidate(race, forecast)` on its actual
pre-off normalized race and saves the compact `masterAnalysis` sidecar.
Its error cannot stop existing publication. Already frozen forecasts
are not rewritten for the experiment. The sidecar has a distinct
`experimental-uncalibrated` status and never sets betting stakes.
Existing `predictionMarks`, `unifiedForecast`, the official R24
recommendation and its receipt SHA remain the incumbent's outputs.

## Mapping from user's 18 parts

1–4: source priority and input acceptance remain in the existing
production ingest and normalizer. This candidate reads only the
normalized pre-off `RaceRecord` and its included evidence; it cannot
browse websites or manufacture missing source values.

5, 10: all active runners are scored with nine categories; prior points
are 24/15/14/15/8/8/6/4/6 = 100. Categories use observed features
only. A missing item has `earned=null`, is excluded from numerator
and denominator, and decreases `coveragePoints`. `score100` is a
renormalized **experimental estimate**, never a score of proven
100-point completeness. Horses with fewer than 35 available category
points remain unscored. Trainer / training / gate / pedigree / video
data not captured by this model are *not inferred* from other columns.
This is a partial implementation of the requested evidence universe.

6–7: existing four-stage pace (start, 3C, 4C, straight) is retained.
Slow / normal / fast straight orders are compared for every horse.
The scenario-robustness heuristic uses mean plus worst-case score;
scenario occurrence probabilities remain null until verified. No
generic inside/outside bias is imputed.

8–9: popularity grades A/B/C are **research flags** based on the
candidate's model rank and *observed* market ranking. An undervalued
horse is a hypothesis only, never a proven edge. Partial odds give
`marketStatus=unavailable` for the full market comparison.

11: candidate probabilities come from a Plackett–Luce finish-order
distribution anchored to the incumbent, with an explicitly **unfitted**
log-strength perturbation. Win probabilities sum to 1, top-two and
top-three are monotonic, and top-three mass sums to 3 for eligible
races. They are not calibrated and cannot support EV claims.

12–14: `ticket_styles` computes exact joint probabilities for
conservative place, a two-head wide hedge, and an outsider wide
conditional on *observed* potential underpricing. It does not treat
multiplication of independent horse probabilities as a ticket chance.
It refuses to invent odds, expected returns or a ¥1,000 stake split.
The production R24 formation remains unchanged.

15–16: evidence-quality confidence B/C/D, missing categories, and
alternate scenario rankings are recorded. No S/A predictive confidence
is claimed without validation. The selection is not forced when
unscored and a speculative longshot is not filled in.

17–18: the per-race sidecar exposes all runner numbers, marks,
scores, coverage, scenario ordering, market risks and research ticket
types for downstream reporting. Existing app presentation is not
replaced by a long narrative; exposing a new detailed screen
requires a separate verified UI release.

## Acceptance gates for an eventual replacement

- Use only captured pre-off inputs and original receipts; reject
  post-result backfill, scratches and winner leakage.
- Pair candidate and v9b on exactly the same race set; report JRA/NAR
  separately, plus debut and jumps (where sufficient data exists).
- Compare ◎ win, ◎ top3, log loss, Brier, R24/B36 return and returns
  excluding the largest payout; evaluate clustered date intervals.
- Run feature ablations and missing-data coverage reports. Reject if
  improved in-sample scoring is bought at the expense of held-out
  win/top3 hit rate or return.
- Refit parameters only on training dates strictly before test dates.
  Do not import held-out results into the published engine.

Commands: `python -m unittest rewrite.test_master_v1 -v`.
