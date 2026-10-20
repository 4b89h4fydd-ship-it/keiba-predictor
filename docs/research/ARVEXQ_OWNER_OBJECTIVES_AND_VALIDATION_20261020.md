# ARVEXQ — Owner research goals and evidence gates (2026-10-20)

Status: research mandate, **not authorization** to activate or publish predictions. Owner goals are targets, never claims of achieved performance.

## North star
Produce useful, reproducible JRA and NAR horse-race forecasts with the main aim of correctly identifying the winner, while seeking high-paying trifecta opportunities and long-run positive returns. Evaluate every runner, reconstruct plausible pace scenarios from information available **before post time**, and consider jockey/trainer/connection incentives only where observable pre-off evidence supports the hypothesis. Do not assert private intentions as fact.

## Acceptance targets (evaluate separately, do not promise)
- At least 80% accuracy, ideally 90% or greater, for published prediction marks / recommended bets as the owner's aspirational target.
- Sustained ROI of at least 100% over independently captured, timestamped, forward data.
- High-payout trifectas remain an explicit goal, but do not optimize payoff at the expense of hiding losing/unscored races.
- Report winner top-1, winner-in-top-3, axis top-3, trifecta hit rate, ROI, uncertainty and sample size **separately**; do not exchange one metric for another. State precisely which mark/bet unit is counted.

## Architecture and constraints
- Keep JRA and NAR acquisition, research, parameters, validation and reporting independent. Keep six independently owned systems: ability, running style, pace, probability, marks, recommended tickets.
- Preserve 200-item partition mandate: distinguish shells, reference wiring, moving real processing, full independence and verified operation.
- Keep existing UI, design, acquisition paths, live predictions and immutable pre-off receipts unchanged unless expressly authorized.
- No main merge, production deployment, model activation or retrospective fabrication without express approval.
- Keep production v3 prediction modules empty until a separately approved, validated algorithm is available.

## Research order
1. Establish pre-off input coverage, horse identity and prior-race history quality; audit missingness and official source identity without inventing history or alternate feeds.
2. Benchmark ability features (full history, recent five and shrinkage), track/circuit/distance/class, trip, time, pace, draw, fitness, jockey/trainer evidence and opponent strength with temporal leakage checks. Prioritize winner discrimination.
3. Construct and compare multiple plausible pace scenarios; calibrate their probabilities rather than assuming equal weights are empirical frequencies.
4. Calibrate separate winner/top-3/exact-order distributions on true out-of-sample cohorts, using log loss, Brier, reliability and candidate ranking.
5. Research role-based marks: ◎【単】 for win suitability and ◎【軸】 for top-3 axis suitability; never imply the mark implies an unverified win rate.
6. Form recommended trifecta tickets from the calibrated ordering distribution, tested against independently available pre-off prices where applicable; record cost, returns, missed wagers and high-payout dependence.

## Measurement protocol
- Pre-register protocol, fixed model/version, full race cohort, captured raw inputs, predictions and spend before each off time using independently verified server witness. Freeze immutable artifacts.
- Track **all scheduled/eligible** races, including unavailable or skipped entries, with separate coverage and conditional-on-scored statistics. No post-race retuning or accidental lookahead.
- Segment JRA/NAR, venue, surface, class, distance, field size and date; track sample sizes and uncertainty, and compare baseline against candidates on the same eligible cohort.
- Record gross returns and total stakes; missing payout means ROI unknown, not zero. Include payout concentration and ROI without top-paying results as sensitivity diagnostics, never retrospectively change evaluation rules.
- Do not promote a model solely because it wins on the development sample. Require independent forward evidence, stable calibration, favorable coverage, risk and economic performance; any promotion to production requires owner approval.

## Current verified research baseline
Stage 64 replayed 527 saved races (JRA 108 / NAR 419); scored 87 JRA / 332 NAR per candidate. NAR recent5 winner top-1 97/332, trifecta 42/332 and ROI 126.61%; shrunk ROI 139.72% but heavily concentrated in 2 large payouts. These are **reused retrospective samples**, not independent forward outcomes. Stage 64 recorded zero independently scored future forecasts. No 80% or 90% accuracy achievement verified.

Source: docs/research/2026-10-19-stage64.md and docs/research/stage64-results/summary.json.
