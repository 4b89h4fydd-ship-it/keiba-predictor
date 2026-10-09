# ARVEXQ — Research feature boundaries

New feature modules are intentionally separated from the large `app.py` and `app.js` files. Do not inline these back into either monolith.

| Feature | Source | Connected execution |
| --- | --- | --- |
| Pre-race fourteen-factor observations | `arvexq/prediction/factor_cards.py` | `race_intelligence.attach_evidence`; no score changes |
| Observed early / middle / last sectionals | `arvexq/prediction/sectional_profile.py` | prefetch attachment; only stored measured values, no gate reaction invention |
| Official condition and AI bias origin | `arvexq/prediction/bias_provenance.py` | prefetch attachment + horse detail display; official status and AI estimate distinct |
| Read-only evidence assembler | `arvexq/prediction/race_intelligence.py` | `scripts/arvexq_prefetch.py` after existing analysis |
| Horse-detail / result UI | `arvexq/ui/static/research/research_view.js` + `research_view.css` | small bridge in app.js, independent fingerprinted static resources |
| Official-result race recap | `arvexq/results/auto_recap.py` | nightly audit; always displays video-unverified status |
| Identified and unlinked horse history | `arvexq/databanks/horse_review_bank.py` | nightly JSON artifact, never global-joins horses by number |
| Independent fourteen-factor role challenger | `arvexq/prediction/factor_challenger.py` | `prerace_archive.seal_detail` before post only, stored with seal |
| Authentic frozen challenge evaluation | `arvexq/backtest/factor_challenger_evaluation.py` | nightly archive audit; checks SHA-256, same original pre-off seal |
| Day-disjoint feature-weight experiment | `arvexq/backtest/factor_weight_calibration.py` | nightly audit (insufficient until many archived dates); `scripts/arvexq_calibrate_archived_factors.py` accepts historical audit JSON |
| Optional expected-return mathematics | `arvexq/backtest/expected_value.py` | analysis-only until third-party calibration and pre-off ticket odds exist |

## Authoritative-state invariants

- No research code modifies existing ◎○▲☆+☆△注, original P1/P2/P3 role predictions, morning selections, betting decisions or official course revision logic.
- Research shadows generated during `seal_detail` are immutable under later odds / outcomes, including after-result restores; no backfilling historic predictions.
- Training reads only hash-verified, captured-before-post evidence and splits by racing DATE, rather than random rows.
- The factor score and percentile are NOT a probability. Historical training, calibration and economic utility cannot be claimed from a synthetic smoke test.
- The product’s production predictor is NOT upgraded to new weights until real forward-validation can establish a reproducible improvement.
- Replays and horse databank records are stored in the nightly GitHub Actions audit artifact. They are not yet a permanent operational D1 horse-memory table.
- Only an official incident note can claim interference; race film is marked not viewed otherwise.
- ARVEXQ’s existing top-page layout is unchanged.
