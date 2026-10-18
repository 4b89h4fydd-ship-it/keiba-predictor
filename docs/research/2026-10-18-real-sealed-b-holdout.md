# ARVEXQ B-model: genuine sealed historical holdout, 2026-10-18

Evidence: [GitHub Actions run 39109130771](https://github.com/4b89h4fydd-ship-it/keiba-predictor/actions/runs/39109130771). The CI independently retrieved dated D1 details for October 7–13, 2026, and performed its actual fit and later-day assessment, using research-only `arvexq.prediction.learned_scenarios`. No odds, existing marks, existing bet choices or present-race result fields entered inference. Old forecasts, if present, served only as independent timestamps of original pre-off availability.

## Audited coverage

- D1 race identities: **396**; genuine original pre-off seal plus strict full-field confirmed result: **198**.
- Excluded: **159** without an authentic original pre-off seal; **39** with incomplete or ambiguous result labels.
- Independent chronology by **whole race dates**, segregated by JRA/NAR and flat/jumps/banei.
- JRA flat: only 37 eligible on 3 distinct days; JRA jumps: 1; NAR banei: 19 on 3 days. **No defensible out-of-sample claim** for any of these groups.
- NAR flat: 141 races spanning 7 days, partitioned as 47 training races (through October 10), 21 validation candidates (October 11, one could not be scored), and 73 entirely later test races (October 12–13).

## Actual later NAR-flat holdout (73 races)

| Metric | Measured |
| --- | ---: |
| Winner first-choice rate | **32.88%** (24/73) |
| Actual winner in three highest win probabilities | **64.38%** (47/73) |
| Correct unordered 3-horse podium | **15.07%** (11/73) |
| Correct exact 1st→2nd→3rd podium | **2.74%** (2/73) |
| Winner negative log likelihood | **2.12412** |
| Equal-runner-probability baseline negative log likelihood | **2.32433** |
| Exact-order negative log likelihood | **6.12417** |

Validation winner first choice was 10% (2/20), which is a major stability warning, **not** evidence of a repeatable improvement. No hyperparameter selection on the later test was permitted and no statistically significant improvement over an approved live predictor has been demonstrated. The smaller exploratory 47-race training sample is **not sufficient to authorize promotion**. The model is not calibrated and is not approved for live win/ticket claims.

## Decision and next requirements

**Rejected for production at this stage.** In particular, 80% winner, podium or ticket accuracy was not demonstrated. Do not install or secretly revive retired scoring, marks or bets to make a non-empty app. Require a substantially larger independently sealed JRA/NAR training corpus, a subsequent untouched forward holdout, probability calibration, and live pre-off race publication verification. Preserve immutable originals and current UI.

The script stores its source/holdout counts, cross-day splits, exclusions, model integrity hash, win-log-loss and ordered-podium metrics in the CI artifact. No payout/return claims are made.
