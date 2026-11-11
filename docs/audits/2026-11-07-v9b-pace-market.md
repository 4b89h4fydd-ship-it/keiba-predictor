# 2026-11-07 | ARVEXQ v9b / v26 pace-market diagnostic & research implementation

## Source and scope

The following v9b/v26 performance and effective attribution are **operator-supplied** numbers, not independently reconstructed from MotherDuck:

- 3,554 runners: live-engine weights exactly matched in operator's replay.
- JRA effective ability/speed about 96%; closing 0.2%; pace multiplier 0.34%; rider 1.7% because same-rider historical overlap about 16%.
- NAR style 0.3%, Elo 3%, never-triggered nominal mass about 6.5%; model/market split JRA 59/41 and NAR 47/53 in the measured blend-eligible group.
- Production v9b 2026-11-04 to 2026-11-07: 194 races, ◎ win 42.3%, B hit 36.6%, B ROI 0.72, ◎ win ROI 0.87.
- 31 JRA: ◎ win 38.7%, B hit 22.6%, B ROI 0.30.
- 163 NAR: ◎ win 42.9%, B hit 39.3%, B ROI 0.80.
- v26 all NAR 104: ◎ win 38.5%, B hit 42.3%, B ROI 0.71. Matched v9b NAR subset: ◎ win 43.3%, B ROI 0.88. v26 JRA today-only 31: ◎ win 41.9%, B ROI 0.43, ◎ win ROI 1.25.

**Important:** v26 NAR all-time and v9b all-time are different windows. The only meaningful head-to-head is a matched-race subset. JRA 31 race outcomes are unstable. ROI on 36-point B is stakes-weighted payout / stakes, and 1.00 is break-even before other expenses. The cumulative market top favorite win rate (operator says 47.7%) must be measured over the same eligible field and same availability rules before treating it as a head-to-head independent benchmark.

## Direct code findings

- Production v8 weights in rewrite/analysis/shadow_v8.py strongly favor speed, distance, track, top-3 and Elo (by circuit). Missing features are omitted and remaining weights are normalized *per runner*: nominal feature shares are NOT constant causal contribution shares.
- rewrite/analysis/pace.py estimates historical start, 3C, 4C and straight order and three scenarios, but rewrite/analysis/forecast.py only affects strengths with a fixed 0.92 front penalty / 1.08 boost. It does not directly carry scenario-specific conditional finishing probabilities into v9b.
- rewrite/analysis/shadow_v9.py applies temperature 0.6692 then a geometric 0.5 model/market blend when all runner odds are present. An effective information contribution of 53% for market is not the same as a literal interpolation weight 53%.
- rewrite/analysis/ability.py uses same-jockey *horse-specific prior runs*, not a separate rider historical skill across all mounts; low overlap makes the feature sparse.
- Because the base model uses a strong pace-insensitive speed signal, arbitrary extra pace weights or removing the market are **not** proven improvements. Production returns currently do not support a blind change.

## MotherDuck check

my_db.arvexq_analytics.race_snapshots was read-only audited on 2026-11-07:

- 417 unique races, 417 rows, dates 2026-10-15 to 2026-10-22, no missing/short sha field.
- JRA: 72 races / 921 entries; NAR: 345 races / 3,556 entries (4,477 entries total).
- 264 labelled retrospective, 4 preoff-candidate, 149 missing analysisType; those labels cannot be treated as 417 independently sealed v9b forecasts.
- These older snapshots cannot, by themselves, reproduce the operator's 194 v9b races from 2026-11-04 to 2026-11-07. No data was overwritten or altered.

## Competitor capability comparison (public descriptions, not audited accuracy)

- netkeiba AI展開予測: projected queue, pace, final time, each horse's first/last 3F. https://support.keiba.netkeiba.com/hc/ja/articles/39766235535769
- netkeiba Aiエスケープ: scenario/pace and running-style prediction based on race members, then finishing rank prediction. https://yoso.sp.netkeiba.com/yosoka/nar/profile.html?id=329
- Odds Park: separate prediction modes for hit-rate, long-shots, ROI and last-minute variables; includes lineage, rider/trainer, course and market factors. https://faq.oddspark.com/faq/show/2421?category_id=11&site_domain=default
- BIGBRIDGE: short-term form, closing three furlongs, sustained lap speed, course suitability and power are distinct marketed scores. https://www.bigbridge-keiba.jp/about

Public marketing does **not** establish their absolute or causal feature contribution or reproducible out-of-sample ROI.

## Actual change in this branch

- rewrite/analysis/pace_market_candidate.py: **research only**. Preserve the exact old v9b output at pace_scale=0 and market_weight=0.5. For the alternative arms, use only each runner's pre-race historical corners/finish and 3 scenario ranks. Apply scenario-specific evidence-based win-strength adjustments, average by predeclared scenario probabilities and then separately vary market weights of 0, 0.25, 0.5. Require at least two past position observations and >= 50% verified field coverage; otherwise the pace contribution is neutral.
- scripts/arvexq_pace_market_ablation.py: score all arms on identical immutable pre-off race records, reject any mismatch between regenerated original v9b per-horse win probabilities and the frozen published original before grading; recalculate full 36-point B from prediction marks, actual final order, actual 3連単 payout and correct total stake denominator; report ◎ win, win logloss, B hit and ROI by JRA/NAR and train/holdout.
- tests: original v9b parity with and without full odds; synthetic local pace impact, normalization, dead-evidence fallback, current-race leakage guard, B 36 points and replay/provenance failures.

Research candidate still uses synthetic preset pace scenario priors and is **NOT** a calibrated scenario model. Better prediction is not claimed.

## Evaluation / promotion gate

1. Export genuine 2026-11-04..07, race-by-race frozen pre-off source payloads (with *frozen pre-v9b strengths*, as-of odds and genuine v9b win probabilities) and separate official top-three finish/payout, preserving capture timestamps and hashes. Never replace sealed originals with post-race reconstructed input.
2. Replay all eligible rows using the CLI below. Exclude race/horse mismatches rather than silently accepting them. Compare **same races, same odds timing, same B formation** against v9b. Report exclusions and missingness separately.
3. Select candidate parameters using a training prefix ending <= 2026-11-05, assess on later unseen dates. Do not retrospectively tune on the heldout slice. Use paired uncertainty intervals and enough forward days before any production adoption.
4. Promote only if separate JRA/NAR outcomes improve logloss without damaging B ROI, calibration (win and top3), performance on sparse-pace races or other safety guards. Record an explicit model-version boundary. Keep previously issued predictions immutable.
5. Never claim gain from an apparently larger style percentage alone. Video identity remains unverified unless evidence is supplied.

Example: PYTHONPATH=. python scripts/arvexq_pace_market_ablation.py sealed_v9b_matched.jsonl --train-through 2026-11-05

The input contract is defined in the script. Missing actual pre-off rows must not be replaced with retrospective records. No live execution/publish was changed by this branch.
