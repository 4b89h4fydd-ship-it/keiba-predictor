# ARVEXQ Ability / ANA race-ranking challenger (research only)

Inspired by https://qiita.com/tech_tech_pingu/items/2e74165be8564aa18e77 .
No code is copied from the article. It documents an idea, **not proof of profit**.

## Implementation and data contract

- `arvexq/research/ranking_challenger.py` trains independent `LGBMRanker(objective="lambdarank")` heads per **JRA / NAR** and **Ability / ANA**, each with the **race** as the `group` and chronologically separated training / validation / holdout **dates**. No row from the same day can appear in different blocks.
- **Ability** relevance: first=3, second=2, third=1, others=0. Market-based features are excluded.
- **ANA** relevance: `min(3, max(0, pre-race popularity - finishing rank))` for an actual top-three finisher, otherwise 0. Its features include only frozen pre-race market signals and other pre-race evidence. If even one market rank is missing, the **entire race** is excluded from ANA, not just the runner.
- Inputs **must** come from `export_mass_training_dataset.py`, which reads sealed feature snapshots and joins result labels afterwards. This challenger does **not** scrape final results into input features. Conflicting hashes or duplicate horses fail closed; incomplete podiums are excluded.
- The feature vocabulary is selected only from the training period. Scores are **within-race ranking signals**, never absolute win/top-three probabilities and never EV without a separately calibrated model.
- The test report includes `winHitAt1`, `winnerHitAt3`, `top1PodiumRate`, `ndcgAt3`, an outperformance diagnostic, and a market popularity baseline. The report explicitly contains `roi: null`; payout-backed ROI and a direct same-race comparison with frozen v9b must be evaluated separately.
- No app, R24, v9b, API, D1, or production import path is modified. New horse / jump models require their own reliable frozen segmentation before any adoption.

## How to run

```sh
python -m pip install -r requirements-ranking-research.txt
python scripts/export_mass_training_dataset.py /path/to/RaceDataBank.sqlite /tmp/arvexq-frozen.jsonl
python -m arvexq.research.ranking_challenger /tmp/arvexq-frozen.jsonl /tmp/arvexq-ranking-output
python -m unittest tests.test_ranking_challenger -v
```

The CLI reports `insufficient-data` rather than training from too few sealed races. Minimum training count is 40 race groups **per circuit/head**, plus independent validation/test groups. Exports and models stay outside Git. This is an experimental lane and must not be promoted until unseen-date comparisons beat v9b on pre-registered rank/accuracy metrics and payout-backed, outlier-robust ROI, with confidence intervals. Avoid selecting thresholds on the test period.

## Article feature hypothesis and paired holdout

The ITmedia 2025-06-19 interview is treated as a hypothesis source, not as a reproducible edge or a verified model.

The ranking challenger also supports four controlled feature experiments from **already sealed**, source-hashed pre-race mass features. The extra interactions never read outcomes and **Ability** continues to exclude current market observations:

- `baseline`: original frozen inputs without research interactions
- `enhanced`: past-form × opponent, past-position × speed/form, plus ANA-only differences between historical within-race percentile and pre-off market popularity
- `no-position`: enhanced, but no positional evidence at all
- `no-market-gap`: enhanced without the additional history-versus-market differences

These operations do not create new underlying data. Missing corners, training data, horse gear, paddock observations, or private pundit odds are **not** filled with guesses.

Use `--paired` to restrict both heads to the *identical* eligible race groups, choose the blend weight from the validation period only, and compare Ability, ANA and their blend on the same untouched holdout:

```sh
python -m pip install -r requirements-ranking-research.txt
python scripts/export_motherduck_frozen_ranking.py /tmp/arvexq-frozen.jsonl
for mode in baseline enhanced no-position no-market-gap; do
  python -m arvexq.research.ranking_challenger \
    /tmp/arvexq-frozen.jsonl /tmp/arvexq-ranking-output \
    --mode "$mode" --paired
done
```

The optional MotherDuck exporter is read-only and only uses `massFeatureArchive` with `originHashVerified=true` and fully settled `result` labels; it delegates gzip, SHA-256 and source-hash verification to the repository's existing decoder. Its credentials must be supplied through the MotherDuck/DuckDB environment. Do not log tokens, store compressed archives in Git, or treat synthetic tests as genuine race performance.

Each research output contains isolated train/valid/test dates, feature coverage, head metrics, held-out per-race scores and a paired validation-selected blend comparison. Any comparison against **v9b** and any payout-backed **ROI** are explicitly unavailable (`null`) until the same-race immutable v9b publication and actual payoffs are joined. The research branch never writes D1, production forecasts or betting tickets.

### Real-data availability, assessed 2026-11-10

MotherDuck `my_db.arvexq_analytics.race_snapshots` held 1,418 saved races (through Nov 10). Of these, 181 had `massFeatureArchive` and an origin-verified envelope. Result-confirmed archives: **63 JRA races on 3 dates** and **114 NAR races on 8 dates** (177 combined). This is *eligibility before replaying the archive decoder and completeness filters*, not 177 proved usable training groups. It is insufficient to claim a robust out-of-sample improvement or an adopted commercial model. In particular, the recent Nov 4-10 races have no top-level `massFeatureArchive`.

Gates for promotion remain: real SHA-checked extraction, enough forward dates by circuit, identical held-out races versus v9b, ◎ first/top3, winner-top3, NDCG@3, and settled ticket ROI (including largest-payout exclusion) with date-cluster uncertainty.

### Additional article audit (2026-11-10)

Reviewed https://yokokenkeiba.com/keiba-ai-tsukurikata/ and
https://www.issoh.co.jp/tech/details/2321/ alongside the original references.
Their reported results (including synthetic examples) are not ARVEXQ results.
Adopt the methodological checks: deterministic horse-number tie breaks rather
than result order; actual settled payouts rather than average odds; explicit
availability times; identical cohorts for ablations. Do not adopt either
article's profit claims or copy example code into production.

The common `ndcgAt3` now always uses finishing relevance (3/2/1/0), including
ANA evaluation. Previously ANA's task labels changed the meaning of this metric
across heads. ANA training labels remain market-outperformance relevance.
`winnerHitAt5` is also reported. Neither metric is a probability or ROI.

A matching archive hash proves integrity, not pre-off capture time. Existing
snapshots do not themselves contain a capture timestamp. Promotion additionally
requires independently verified publication/capture evidence, explicit flat /
newcomer / jump segmentation, calibrated probabilities and aligned frozen v9b
predictions and R24 settled tickets. Until these gates pass, results remain
exploratory and production must remain unchanged.

### Executed real-data result and non-adoption decision

Flight `521f0ebb-f721-4818-89f2-d60bc6ec8b8b`, version 2, run 2 completed
successfully (exit 0) on 2026-11-10. Run 1 was cancelled after export and
restarted with two LightGBM threads; no parameters were selected from its test
results. The source is retained in the Flight. Reports are in
`ranking-real-run-20261110.json`; no horse archives or credentials are committed.

- SHA-checked restoration: 177 races / 1,914 horses, JRA 63, NAR 114;
  archive dates 2026-10-15 through 2026-10-27.
- Paired NAR eligibility: 61 races / 633 horses; train 48 (through Oct 24),
  validation 7 (Oct 25), test 6 (Oct 26–27). JRA failed the existing minimum
  training gate; the minimum was not lowered.
- Four predeclared modes all completed. All yielded identical results:
  Ability top1 win 1/6, top1 podium 4/6, winner top3 3/6, top5 4/6,
  raw-score finishing NDCG@3 0.4558; ANA 1/6, 3/6, 3/6, 5/6,
  raw-score finishing NDCG@3 0.4119. Market top1 won 3/6.
- Validation chose Ability weight 1.0 in every mode. No beneficial ANA blend.
- Five exact history interaction keys had 0/633 coverage. Therefore the
  ablation is operationally executed but is NOT evidence that the underlying
  historical concepts are ineffective. Investigate vocabulary/availability
  before another experiment; do not infer missing values.
- Paired rank-percentile reports break score ties by horse number, so their
  ANA NDCG (0.4383) differs from raw-score tie-averaged NDCG (0.4119).
  Use raw-score head metrics for the table; preserve this limitation.
- Archived preRacePrediction modelVersion: stage64 85, empirical-fusion 6,
  missing 86; none identifies v9b. Only 89/177 have positive minutesToPostAtSeal.
  Presence of a payout object alone does not prove ticket replay eligibility.

No v9b comparison, calibrated LogLoss/Brier/ECE, ticket ROI, largest-payout
exclusion, R24 strategy comparison, drawdown, date-bootstrap inference or
selection-threshold improvement is claimed. Two test dates cannot establish
robust improvement. Newcomer/jump segmentation and independent feature capture
times remain unverified. These results are exploratory, not a valid promotion
benchmark. The inspected Oct 26–27 holdout is consumed for future model changes;
reserve a new unseen period for any final test.

Do not adopt: accuracy did not beat even the market baseline; comparator,
probability, timing and betting gates are unmet. Keep v9b/R24 and existing
selection conditions. No production API/D1/UI writes were made. Live display,
save-path and deployment verification remain unexecuted. Runtime status exposed
no Cloudflare/D1 credentials, so their availability has not been established.

Verification: 32 pytest tests plus 4 subtests passed (research ranking/export,
archive integrity/legacy guards, retired ranker and production boundaries),
py_compile and git diff --check passed. PR #513 was merged concurrently as
fee9449f; this follow-up rebases only the new changes onto that main.
