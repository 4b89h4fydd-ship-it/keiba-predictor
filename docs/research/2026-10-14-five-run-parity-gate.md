# ARVEXQ: cross-language five-run evidence parity gate (2026-10-14 JST)

## Decision

**Production model replacement: NOT APPROVED.** This change repairs a proven inconsistency between Python and browser ingestion of the SAME five-run observations. It does not change model weights, inject a new signal, rewrite historical pre-off forecasts, or claim improved prediction accuracy.

Reviewed repository: `4b89h4fydd-ship-it/keiba-predictor`, base `main` at `5c4e9949b1d93f9de9409c3a3a4881bb8d337d2b`. Code paths: `arvexq/prediction/past_performance.py`, `arvexq/prediction/factor_model.py`, `arvexq/ingest/full_career.py`, and `arvexq/ui/static/app.js` (`arvexqFactorValues`).

## Root cause and reproducible test

The authoritative Python past-run collector normalizes date formats (`YYYYMMDD`, `YYYY/MM/DD`, `YYYY.MM.DD`), combines all supported history keys, merges duplicate runs on the same date, and excludes current-day/future races. The browser previously sorted raw date strings, considered only `recentRaces`/`allPastRuns`, and deduplicated by multiple noncanonical fields. The same physical racing history could produce different TRUE RUN/PURE/SECTIONAL features, coverages and marks on browser and server.

Test added to `scripts/arvexq_three_factor_parity_smoke.js`: invoke the actual browser `arvexqFactorValues` function and the actual Python `collect_horse_raw_metrics` function using four deterministic cases (mixed date formats, complementary duplicated records, alternate history lane, future-only records). Each compares feature availability, factor values and resulting unchanged 45/35/20 score; no fabricated finish results or accuracy measurements.

- Red baseline: commit `985b81cf4325f1cd2f86a3eabb209361eac2c323`, [validation run 38435600500](https://github.com/4b89h4fydd-ship-it/keiba-predictor/actions/runs/38435600500) **failed**. In the mixed-date case, JS coverage was 0 while Python coverage was 3.
- Fix: commit `1e9e4bc18e04e04633d4e4f1944a69cd223b0709`, applied only to the browser's prior five-run collector and deduplication.
- Green verification: [validation run 38435841250](https://github.com/4b89h4fydd-ship-it/keiba-predictor/actions/runs/38435841250) **succeeded**, including full CI workflow steps for Python temporal analysis, browser mark/ticket smoke, racecard delivery and static PWA build.
- No production data were changed by this PR; whether a successful main merge deployed to Cloudflare must be separately audited.

## Previously measured evidence; do NOT attribute to the current 45/35/20 model

The published repository audit [2026-10-13/README.md](2026-10-13/README.md) recorded 396 races (October 7–13, 2026), of which 235 had evaluable pre-off sealed forecasts from historical model version `evidence-v317-consensus-rebuild`. In the later 108-race test block, the stored decision baseline and a proposed P1 power calibration had respectively:

| Metric | Historical sealed baseline | Proposed correction |
|---|---:|---:|
| Top-1 winner hit | 27.78% | 28.70% |
| Winner top-3 capture | 56.48% | 55.56% |
| Winner Log Loss | 2.11266 | 2.14669 |
| Multiclass Brier (unnormalized by runners) | 0.83641 | 0.84742 |

The candidate is rejected because the loss metrics worsened and no independent improvement is established. The historical locked model is not the latest `arvexq-true-run-pure-sectional-45-35-20-v2`; none of these values is a valid measurement of current main accuracy.

Static archive coverage audit for 3,044 horses (268 SHA256-verifiable source snapshots): missing TRUE RUN 221/3,044, PURE 221/3,044, and the input used by SECTIONAL (published last-600-metre *rank/percentile*) 3,044/3,044. Finishing *time* alone is not interchangeable with a rank. In this archive subset all sectional contributions are the common neutral `0.20 * 0.5 = 0.10`; they cannot distinguish horses. The current A-grade gate also requires all three factor observations, so that gate cannot produce A from such missing raw inputs. **This is a data-acquisition and confidence-gating problem, not proof of a better alternative weighting.**

Past archived P1/P2/P3 position probabilities violated horse-level mutual exclusivity in 49 of 235 races; current main's PL formula and uncalibrated research distribution must not be conflated with those archived forecasts. The mathematical research module is not evidence of observed winning probabilities.

## Safety and further verification

- Core `factor_model.py` weighting and Python score path untouched.
- Historical `preRacePrediction`, `preRaceBet`, immutable snapshots and results untouched.
- Prediction display after post time continues to rely on existing immutable pre-off receipts; corresponding CI regression completed.
- Main integration requires a green validation on the final head and a clean base merge. No branch-protection or deployment rules should be bypassed.
- Cloudflare API deployment status and real iPhone PWA behaviour remain **unverified in this audit**, regardless of GitHub CI outcome.
- An improved win rate, long-run betting return, better market comparison, or independently calibrated A/B/C confidence has **not** been established.

## Remaining research gates

1. Obtain timestamped and provenance-verified pre-off input snapshots; independently audit all-race coverage, missingness, scratch status, source times and frozen bets.
2. Trace published last-600-metre timing versus rank fields through the ingestion pipeline; do not fabricate sectional observations.
3. On new unseen date blocks, compare the current frozen 45/35/20 model, a market-odds baseline at the SAME pre-off time, and separately trained conditional multinomial-logit/boosted models using race-group splits.
4. Learn and calibrate winner and ordered finish distributions, then evaluate Log Loss, Brier, top-1/top-3, calibration, subgroup degradation and loss confidence intervals. Calibrate role marks, and ticket hit/ROI separately.
5. Promote a replacement only after predefined independent promotion checks. Remove older scorers only when validated runtime callers, archived invariants and full UI tests pass.
