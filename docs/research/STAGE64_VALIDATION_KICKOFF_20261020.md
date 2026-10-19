# Stage64 validation kickoff — 2026-10-20

## Request
Owner authorized **research validation**, not production deployment or adoption of a new forecast model.

## Verified GitHub receipts
- Current branch: `feature/arvexq-v3-data-boundary-empty-prediction-20261019`; PR #367 draft.
- Stage64 Shadow Research CI run [39291144088](https://github.com/4b89h4fydd-ship-it/keiba-predictor/actions/runs/39291144088) completed successfully for commit `634992dda3452edb0e84556208913c3ebc13e597`.
- Earlier preregistration run [39266625982](https://github.com/4b89h4fydd-ship-it/keiba-predictor/actions/runs/39266625982) `shadow` job succeeded, including shadow tests and two upload-artifact steps. Freeze steps were **skipped**, as expected for preregistration.
- Existing preregistration readback lists JRA plan artifact `12192643073`, NAR plan artifact `12192483600`, both verified before planned period.
- Stage64 archived 527 race validation (JRA 108, NAR 419; scored JRA 87, NAR 332) is **retrospective reused development evidence**, not independent forward accuracy.
- Existing published status: `futureForecastRaces=0`, `independentScoredRaces=0`. Do not change these counters without new artifacts.

## Checkpoints for live forward validation
1. Confirm the exact pre-off saved-data artifact ID, member name, capture time, eligible race IDs and corresponding verified plan artifact **before** dispatching freeze.
2. Run only the existing Stage64 shadow workflow `freeze` for JRA and NAR separately. Its action requires authenticated artifact IDs; never invent them and never backdate.
3. Verify workflow completion server timestamp before every race off time, forecast file digest and complete racing cohort. Exclude invalid forecasts transparently.
4. Once genuine confirmed results exist, use `capture-results` and `score`, and publish denominators, missingness, win-top1, winner-top3, axis-top3, trifecta hits, payouts and ROI by circuit and candidate.
5. Analyze model discrimination and calibration, losing cases, forecast coverage and high-payout dependence; preserve preregistered candidates untouched during window.

## Current execution boundary
Research CI has run. No new user-authorized `freeze` workflow was dispatched in this handoff because the GitHub connector here exposes run inspection but **no workflow_dispatch action**, and no fresh pre-off source artifact ID was independently established. Therefore **independent live forecast validation has not started**, and no future-race hit rates may be claimed.

No production/model/UI/data-acquisition changes. No merge or deployment.
