# ARVEXQ three-analysis replacement — research branch only

The retired six-stage Stage63/Stage64 algorithm has been removed from this branch.
Do not merge or deploy this draft without meeting the acceptance criteria.

## Architecture

- Official JRA/NAR history (unchanged existing acquisition) -> horse ability evidence.
- Locally permitted historic video -> detected horse boxes -> temporary track IDs -> independently verified permanent horse IDs + per-frame meter calibration -> INTERNAL speed / early response / path / slowdown evidence.
- Past initial-corner observations, starting gate, frame and field pressure -> race-development evidence.
- Separate learned circuit coefficients + independently calibrated scenario weights -> top-three joint distribution -> win/3着内 probabilities -> ◎○▲△☆ and REAL-ODDS 3連系 candidates.
- UI does not receive frames, track IDs or internal video metrics.

The new model fails closed when not calibrated. No stage64 fallback or invented odds.
Old immutable saved race evidence is preserved in D1 but not advertised as a new
forecast; official past runs, races and user records are not deleted.

## New code

- `arvexq/forecast/new_method.py`: explicit inference contract.
- `arvexq/forecast/training.py`: chronologically separated fitting/calibration/holdout evaluator.
- `arvexq/forecast/video_tracking.py`: authorized local video detector/tracker and verified metric features.
- `arvexq/forecast/engine.py`, `marks.py`, `tickets.py`, `publication.py`: new production boundary on this branch ONLY.

## Required acceptance gates

1. Restore existing D1 full snapshots through `arvexq_fetch_d1_bundle.py` and
   verify race IDs, dates, all starters, historical runs and finishers.
   No new provider route should be added.
2. Ensure past-run and video samples precede each target race.
3. Obtain lawful, testable video clips and a separate trained ONNX model.
   Track every starter with verified horse IDs and ground-plane calibration.
   Synthetic tracking tests are NOT evidence of actual racing accuracy.
4. Fit CENTRAL and LOCAL models separately. Train/validation/test dates must
   be strictly disjoint. No outcomes, final odds or retrospective snapshots may
   leak into the pre-off feature vector.
5. Empirically derive and validate pace scenario occurrence probabilities.
   `scenarioWeightsValidated` is FALSE until that measurement is available.
6. Temperature-calibrate win probability and compare Brier/log loss/◎1着,
   ◎3着内 and 3連単・3連複 hit and return rates on untouched holdout races,
   with and without video on the same race population. Do not report ROI
   without a time-verified pre-off wager-odds and stake ledger.
7. Run complete repository CI, D1 readback and iPhone/PWA display checks
   before any separate authorization to merge or deploy.

## Current remaining blockers

- No per-circuit trained-and-calibrated vnext model artifacts.
- No independently measured pace scenario frequency.
- No real, verified all-field horse video tracking or matched lift comparison.
- No proven live D1 -> official odds -> 3連系 ticket recommendation coverage.
- Production deployment and mobile rendering have not been verified.

## 2026-10-25: Actual preserved D1 evidence (read-only MotherDuck research run)

Read-only MotherDuck Flight `824ed29b-e3c7-46ab-a1dd-683f9717bedd`, run 1, **SUCCEEDED**.
No MotherDuck data was inserted, overwritten or used as a new provider route.

| Evidence | Measured |
| --- | ---: |
| Full snapshots restored with SHA check | 401/401 |
| Finalized races | 399 |
| Races with historical runs | 385 |
| Valid local training-label rows | 197 |
| Valid central training-label rows | 46 |
| Video feature rows | 0 |
| Race-lap series | 0 |

Using the **existing** `forecast/training.py` and `forecast/new_method.py`:

- NAR: 97 races fit (October 15–18), 32 races temperature-calibrated
  (October 19), 68 race strictly later holdout (October 20–21).
  **Winner pick hit 19/68 = 27.94%**, holdout winner log-loss 2.0297,
  mean win Brier 0.08229. No verified 3-way quotes/stake ledger -> ROI NOT MEASURED.
- JRA: 23 races fitted October 17, 23 temperature-calibrated October 18.
  **No later eligible holdout**, so no JRA winner-hit estimate can be reported.
- Missing verified all-runner videos and race pace scenario labels mean
  neither video lift nor true scenario calibration is measurable.
  No model is accepted for production or advertised as satisfying targets.
- In particular, `train()` cannot set `outOfSampleValidated=true`
  because the same temperature-validation rows are not independent holdout.

Do **not** interpret ordinary Python/JS CI passing as proof that production
can calculate a valid race prediction. The model directory remains empty, and
`scenarioWeightsValidated` stays false. The draft PR is intentionally not
merged or deployed because it would suppress real predictions.
