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

### Real-data availability, assessed 2026-11-11

MotherDuck `my_db.arvexq_analytics.race_snapshots` held 1,418 saved races (through Nov 10). Of these, 181 had `massFeatureArchive` and an origin-verified envelope. Result-confirmed archives: **63 JRA races on 3 dates** and **114 NAR races on 8 dates** (177 combined). This is *eligibility before replaying the archive decoder and completeness filters*, not 177 proved usable training groups. It is insufficient to claim a robust out-of-sample improvement or an adopted commercial model. In particular, the recent Nov 4-10 races have no top-level `massFeatureArchive`.

Gates for promotion remain: real SHA-checked extraction, enough forward dates by circuit, identical held-out races versus v9b, ◎ first/top3, winner-top3, NDCG@3, and settled ticket ROI (including largest-payout exclusion) with date-cluster uncertainty.
