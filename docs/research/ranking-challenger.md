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