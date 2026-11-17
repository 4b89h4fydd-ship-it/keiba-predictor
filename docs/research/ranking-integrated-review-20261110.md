# Integrated LTR research: final eligibility review, 2026-11-10

## Decision and status

**JRA: insufficient data. NAR: insufficient unseen data. Production unchanged.**
PR513 was merged into main fee9449f; continue the open PR514. No uncommitted
user changes were present. Earlier 177-race/1,914-runner and 16-fit reports are
retained as exploratory history, not certified tests. Oct25 and Oct26–27 must
not be reused as unseen tests. Neither training success nor this report proves
commercial accuracy or profitable betting.

## Implemented comparison

`ranking_challenger.py` supports fixed learner/label combinations, sharing the
same paired Ability/ANA cohorts, train-only feature vocabulary and date blocks:

- Existing Ability = LightGBM LambdaMART/lambdarank, relevance3/2/1/0. They are
  the same implementation, not two independently different models.
- ANA retains market-outperformance labels.
- Pointwise LightGBM regression uses the same graded labels without race loss.
- XGBoost3.4.1 `rank:ndcg`, topk pair construction, graded labels.
- Winner LTR uses1 for winner,0 otherwise; podium LTR uses1 for ranks1–3.

`ranking_benchmark.py` executes all six unique variants separately for JRA/NAR.
No hyperparameter search is claimed: one predeclared conservative parameter set
per learner,200 estimators maximum, validation early stopping25, two CPU
threads. A one-date validation set cannot support a credible search. Record
fit seconds, process peak RSS (cumulative KiB, not per-model incremental RAM),
model bytes and inspectable validation scorecards. Metrics add Top2,MRR,
NDCG@1/5,podium counts and recall to existing Top1/Top3/Top5/NDCG@3.

Ranking scores remain scores. `ranking_probability.py` separately implements
race softmax win and Plackett–Luce podium inclusion candidates, temperature
selection, win LogLoss/multiclass Brier/ECE/calibration bins and podium Brier.
It requires training strictly before calibration, at least two calibration
dates and two later test dates with disjoint race_ids. Sum-to-one/three is a
consistency check, not a calibration claim. Only synthetic contracts were
executed for calibration. No real calibration/test sample exists here.
It also implements paired date-cluster bootstrap and exact settled ticket cash
flow accounting, including largest-payout removal with all stakes retained.
No payouts are guessed from odds. No R24/B36 strategy is invented or replayed.

## Newly discovered roster-quality defect

The old exporter silently joined only runners with a finish label. That can
shrink a frozen query when results are partial, runners cancel or fail to
finish. Now reject the ENTIRE race if joined runner count differs from the
original archive horseCount. Do not fabricate finishing ranks or retroactively
change the frozen roster. Dead heats/duplicate finishing ranks are excluded by
prepare_races until a dedicated label policy exists. Unresolved cancellation,
DNF/disqualification feeds are excluded rather than silently relabelled.

Run5 completed12 preliminary model fits before this repair; its results are
preserved in `ranking-multimodel-20261110.json` but superseded for eligibility.
Run6/version8 completed the strict export/comparison successfully (exit0):

-177 origin-valid labelled archives ->152 full-roster races/1,725 runners;
 25 incomplete frozen rosters excluded; JRA55,NAR97 before paired filters.
- JRA paired development cohort53 races/671 runners over3 dates: train36
 (Oct17/24), validation17(Oct25). Minimum40 means deficit4; all six fits
 intentionally refused. No strict JRA model performance is available.
- NAR paired development cohort48 races/513 runners over5 dates: train44
 (Oct15/17/23/24), validation4(Oct25), test0. Six model fits completed.
- Exact cohort metadata independently recomputed by version9/run7(exit0),
  in `ranking-cohort-audit-20261110.json`.

| NAR model | Top1 win | Top1 podium | Winner Top3 | NDCG@3 | MRR |
|---|---:|---:|---:|---:|---:|
| Ability / LightGBM LambdaMART |75%|75%|75%|0.6438|0.8125|
| ANA |0%|50%|0%|0.2956|0.1285|
| Pointwise LightGBM |75%|75%|100%|0.7044|0.8750|
| XGBoost rank:ndcg |75%|75%|100%|0.7888|0.8333|
| Winner-only LTR |50%|50%|100%|0.7569|0.7083|
| Podium-only LTR |75%|75%|75%|0.6438|0.8125|

All are development/early-stopping metrics on just four races. Against Ability,
Pointwise/XGBoost win-hit difference0, winner-only−25points, ANA−75points.
Paired records and wins/losses are saved in
`ranking-complete-roster-20261110.json`. Date bootstrap reports one date and
CI=null, never a spurious narrow interval. No statistical improvement is claimed.

## Feature quality and opponent coverage

Previous reporting repair remains: input versus selected coverage is separate,
and actual zero differs from NaN. The earlier broad development cohorts had
form100% both circuits, opponent99.59%JRA/28.99%NAR. These are different cohorts
from the new strict export and must not be directly labelled before/after gains.
Strict NAR form513/513=100%, opponent144/513=28.07%, both retained by the model.
Position/published-speed/relative-closing archive columns remain0%; no fill.
Strict JRA selection coverage is not applicable because training was refused.

Audit of10,289 historical row observations (not unique runs) in NAR archived
race payloads: explicit opponentLevel0, explicit class4,617,title10,213,
JRA class parser recognizes2,408 titles. Common unrecognized names areC1,C2,
C3,B2,age-class titles and full-width variants. Classification of evidence:

1.Source availability: numerical opponent strength is absent in saved source;
  underlying publisher availability remains unverified.
2.Acquisition failure: not proved; cannot distinguish unavailable from missing
  acquisition without independent provider records.
3.Normalization: confirmed use of JRA title patterns on NAR classes. Preserve
  explicit native classes as NFKC-normalized,track-scoped categorical history
  counts for future snapshots; do not manufacture a common numerical scale.
4.Historical linking: no independent linkage completeness proof; unresolved.
5.Generation: cornerPositions/last3fRank aliases repaired previously; native
  class categoricals added, tested on source-shaped fixtures.
6.Selection: bounded percentile exclusion repaired previously; strict NAR
  observed hypothesis columns are retained.
7.Other: frozen legacy matrices cannot be rebuilt with post-race enrichment.

New native-class features are NOT present in old sealed matrices, so no real
accuracy gain from them is claimed. Feature schema advances to v4. Native
class frequency is a source observation, not opponent Elo. Newmaiden/jump
segmentation and source-attested per-feature timestamps remain unverified.
No independent newmaiden/jump model was trained.

## Central large-field findings and limits

Earlier enhanced Ability had0/10 wins and1/10 winner-Top3 for13+ runners;
small fields had3/4 wins,Tokyo3/6,Kyoto2/9,Niigata0/5. These were on one
existing development date, before full-roster screening. Pointwise had40%
and XGBoost35% overall versus Ability30% in the preliminary20-race cohort.
Those comparisons are NOT evidence of unseen improvement and cannot separate
field size from course/distance/class/popularity composition or missing labels.
Strict JRA now lacks four training races. Do not add a large-field handicap,
exclude tracks, or assert a causal pace/jockey explanation from this evidence.
Winning-horse ranks and track/distance/field slices remain inspectable in prior
validation reports; complete causal feature-level attribution remains unmet.

## Selection and prospective collection

The final frontend gate in `morning/selection_cut.js` requires selected=true,
hitRate>=.80,hitRateSamples>=30,hitRateWilsonLower>=.65,primaryType and types
containing 的中重視型,positive raceNumber; sorts chronologically with no daily
cap. These are downstream filters, not verified calibrated race probabilities.
The generic SelectionPolicy helper alone is not the deployed policy definition.
No threshold was changed. Gap,uncertainty,odds/EV and coverage are future
candidates,not accepted criteria. Buying count,skip rate and ROI comparisons
cannot be reported without sealed original tickets and actual settled returns.

Reuse the existing provisional read-only pre-off collector rather than create a
second acquisition path. It now preserves source model version/marks/bets and
forecast separately OUTSIDE features, plus observed-at provenance and the source
oddsUpdatedAt. It rejects post-race outcomes, checks post time and writes with
no overwrite. It remains explicitly provisional, not independently attested.
Actual execution on Nov10T16:54UTC found0 due candidates and captured0; this is
not a new labelled dataset or model validation. Artifact:
`/tmp/arvexq-future-captures/provisional-20261110T165444370848Z.json.gz`.
The previous source audit remains valid: local SQLite race tables empty;
Nov8 D1 public export71 active races had no sealed features/preRacePrediction.

## Remaining gates and artifact limitation

No trustworthy same-time v9b probability/ticket comparator exists for these
cohorts. Real LogLoss/Brier before/after,win/place/R24/B36 hit and ROI,
largest-payout-excluded ROI,model blend and strict-selection improvement remain
unexecuted. Need at least4 later independent dates to meet the implemented
calibration2-date plus test2-date guard; that is an implementation minimum,
NOT a statistical power claim. More races/dates are needed for robust adoption.

Estimator/vectorizer/scorecards were saved under the isolated Flight scratch
`/tmp/arvexq-benchmark/models`,not production. Durable retrieval was NOT completed.
Automatic approval review rejected the proposed base64 model-archive log export
as sensitive egress of private-data-derived models without specific approval.
That export was never run; its source was removed. No workaround was used.
No durable model artifact is claimed. Summary reports, code and versioned Flight
sources are retained for reproducibility, subject to rerunning dependencies.

## Checks

64 local tests +8 subtests passed,covering genuine estimator fitting on synthetic
race groups,consumed-date exclusion,probability sums and calibration boundaries,
actual cash flows,complete rosters,native-class categories and production guards.
CI initially failed because XGBoost3.4.1 requires Python>=3.12,then because a
pytest collector contract lacked pytest. Fix both; pin research model libraries
and execute collector contracts via pytest. Subsequent CI result is recorded in
PR514. Scientific limitations and data shortages are not waived by passing CI.
