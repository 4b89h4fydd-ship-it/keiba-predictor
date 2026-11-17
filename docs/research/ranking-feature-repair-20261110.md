# Feature path repair and development-only retraining, 2026-11-10

## Source state and decision

Latest fetched main was fee9449f (PR #513 merged); #514 remained open at
84bae69f. Continue #514 rather than duplicate its fixes. No production model,
R24 strategy, API or D1 write is authorized by these findings: adoption remains
**not established**. This is not an unseen-test improvement report.

## Root causes and fixes

1. `mass_feature_factory` generates history and relative features; the snapshot
   pruner preserves their exact w5 keys; the SHA-checked archive decoder restores
   them; training JSONL joins only settled labels.
2. `feature_manifest` ranked columns by coverage multiplied by standard
   deviation. Large-unit variables crowded bounded percentiles and research
   interactions out of the 1,000-column cap. Use coverage-based selection and
   reserve the prespecified, varying hypothesis columns, fitted on training only.
3. Coverage was calculated **after mutating the vectors to selected columns**.
   Report input and selected coverage separately. Previously reported 0% was
   not evidence that historical form/opponent information was unavailable.
4. DictVectorizer implicitly replaced absent numeric evidence with zero.
   The matrix now keeps absence as NaN and observed 0 as 0.
5. Ingestion uses `cornerPositions` and `last3fRank`; the factory did not read
   those forms. Add last-corner parsing, explicit/unambiguous corner1/corner3
   extraction and lower-case closing-rank alias. Do not guess numbered corners
   from partial lists. Add a separate seconds namespace for `marginSeconds` /
   `timeBehindWinner`, without mixing seconds and finishing-margin units.
   Bump the feature schema. Existing sealed snapshots/hashes are never rebuilt.

The source corner/closing fixes apply to future snapshot creation only. The
archive retraining uses immutable original vectors; it does not invent missing
position or closing evidence from post-race horse histories.

## Audited data

- MotherDuck: 1,418 race rows, Oct15–Nov10, 181 archived matrices. Settled
  restoration: 177 races / 1,914 horses (JRA 63, NAR 114), unchanged from run2.
- All 181 origin-verified matrices diagnostic: JRA 67 races/857 horses and
  NAR 114/1,212. Form percentile exists in 857/857 and 1,212/1,212;
  opponent percentile in 854/857 and 276/1,212 respectively. Position,
  published speed and relative closing keys are absent in this archive family.
- Local static manifests: 1,803 entries (JRA300 across10 dates, NAR1503
  across32 dates). Verified each referenced blob SHA256 and race identity.
  388 entries contain a matrix/archive. Origin/label audit: 68 invalid origin
  hashes, 274 without usable settled labels, 10 origin-valid labelled candidates
  (JRA9 on Oct17; NAR1 on Oct10;118 horses). No new untouched test date.
  Standalone snapshot capture times still need authentication before training.
- Local race/prepared/central/NAR SQLite tables each contain 0 race rows.
- D1 public GET with the descriptive research user-agent succeeds (health200;
  default urllib agent403). Nov8 fetch:71 active races/details,0 missing;
 12 retired Banei summaries excluded. None contains a mass matrix/archive or
  sealed `preRacePrediction`. Do not relabel current post-race predictions as
  original v9b publications. Root UI GET200 verifies reachability only.
- Raw historical field names were audited for availability, not used to rebuild
  sealed feature vectors. No database or prediction was overwritten.

## Restored coverage and executed training

Flight521f0ebb-f721-4818-89f2-d60bc6ec8b8b version3/run3 exited0.
Full output: `ranking-development-retrain-20261110.json`.

Only dates through Oct25 participate; Oct26–27 are consumed and excluded.
Minimum training40 is retained. The final available day is validation, and
there is **no test block**. Validation also controls early stopping, so these
numbers are development diagnostics, not unbiased estimates.

- JRA:61 races/738 horses,3 dates; train41 on2 dates, validation20 on Oct25.
- NAR:55 races/576 horses,6 dates; train48 on5 dates, validation7 on Oct25.
- Both heads and all four modes completed:16 model fits.
- Input/selected form coverage: JRA738/738=100%, NAR576/576=100%.
- Input/selected opponent coverage: JRA735/738=99.59%, NAR167/576=28.99%.
  Old selected-column report was0% for both. This restores access to already
  observed evidence, not the underlying data collection rate.
- Position, speed-index and relative closing coverage remain0%; no imputation.

| Circuit / model | Top1 win | Top1 podium | Winner Top3 | Winner Top5 | NDCG@3 |
|---|---:|---:|---:|---:|---:|
| JRA baseline Ability |30%|65%|50%|60%|0.4219|
| JRA enhanced Ability |25%|65%|45%|60%|0.4404|
| JRA baseline ANA |20%|30%|25%|40%|0.2845|
| JRA enhanced ANA |15%|35%|35%|55%|0.3094|
| NAR baseline Ability |71.43%|85.71%|85.71%|100%|0.5818|
| NAR enhanced Ability |71.43%|100%|85.71%|100%|0.7096|
| NAR baseline/enhanced ANA |14.29%|57.14%|14.29%|28.57%|0.2794|

JRA no-market-gap ANA reaches25% Top1, versus15% enhanced; adding gaps does
not establish a benefit. No-position equals enhanced because the source
position columns are absent. NAR enhancements improve development NDCG/podium
but not Top1 wins; JRA enhancements reduce Top1 wins. No configuration is
accepted on these validation results. Market Top1 wins: JRA25%, NAR57.14%.
ANA's market-outperformance objective does not substitute for win accuracy.

## Unmet evidence gates

v9b frozen same-race predictions, R24 original tickets, independently sealed
pre-off odds and capture timestamps are not established for these cohorts.
No v9b blend, probability calibration, LogLoss/Brier, win/place/R24 ROI,
largest-payout-excluded ROI or selection threshold improvement is reported.
Each validation circuit has one date: a date bootstrap cannot measure
between-day uncertainty. No unseen-test races were scored. Independent new
flat/newcomer/jump segmentation also remains unverified; no promotion claim.
Keep R24 and strict-selection conditions unchanged. Existing source values
were not backfilled with guesses; class-based opponent level is a proxy,
not measured opponent Elo. Per-race descriptive validation errors are added
for winner rank, selected horse finish/popularity, track and field size;
missing corner evidence prevents causal explanations about pace.

## Completed error replay and checks

Flight version4/run4 also succeeded (exit0), replaying the same development
cohort to emit errors, without scoring the consumed test. Raw per-race errors
and track/field-size slices: `ranking-validation-errors-20261110.json`.
Distance metadata is joined by race_id from MotherDuck after prediction for
reporting only, never as a post-hoc model input.

Enhanced JRA Ability: 13+ runners 0/10 Top1 wins, winner Top3 1/10;
8 or fewer runners3/4 wins. Tokyo3/6 wins, Kyoto2/9, Niigata0/5.
Enhanced NAR Ability: Morioka3/3, Kanazawa1/3, Kochi1/1 wins. Its two
missed winners ranked5 and3. ANA's six missed NAR winners ranked8,10,4,9,8,11:
market-outperformance training did not rank the actual winners well on this
validation day. These tiny slices motivate future hypotheses, not exclusions
or causal claims about luck, jockeys or pace. No selection condition changes.

43 local pytest tests plus4 subtests passed, including consumed-date exclusion,
NaN-vs-zero, bounded-feature retention, ingested corner/closing aliases,
numbered-corner ablation, frozen archive and production-boundary regressions.
GitHub Actions research run42855476150 passed on code commit2988b04c;
run42855283245 passed on a9215cd8. Remaining changes after that check only
save error/metadata reports. No production deployment or live save test.
