# 2026-10-21 | NAR contextual evidence integration (not active forecasting)

## Goal and externally observed method
Review of the public "地方競馬ウォッチ" explanations and publicly accessible note articles identified:
- historical lap / first-600m observations, pace competition and prior-trip interpretation,
- course bias measured separately from official going,
- riders / transfers, odds history and time-stamped evidence,
- immutable pre-off predictions with all outcomes publicly scored.

Sources: https://yukochi.com/how ; https://yukochi.com/about ; https://yukochi.com/record ; https://note.com/saga_you/n/n2a28e43aac04 .
The website's proprietary model, video measurement code, charts, datasets and paid predictions are **not** copied. The implementation is an independently specified research feature adapter.

## Implemented connections
The existing \`build_horse_features\` / \`build_race_feature_matrix\` / \`build_mass_feature_snapshot\` / \`prune_matrix_for_snapshot\` path is retained. No new data fetcher, API, background job, prediction model, bet generation, model weights or display changes are installed.

\`arvexq/prediction/nar_context_features.py\` supplies sparse and optional observations **only for NAR flat racing** (excludes central and banei):
- historical first-corner relative placement, front-rate and front-fade rate (observed outcomes, not measured gate speed);
- reviewed first-600m *race-level* sectionals, only for matched track, distance ±100m, surface and going, with recorded source kind + reference (not horse-level speed);
- reviewed video / official-stewards structured trip incidents; no keyword guessing, and missing annotations remain missing;
- riding change / previous JRA-track exposure indicators from a dated prior run;
- explicitly sourced, timestamped and historically observed *pre-off* track-bias estimates (not official track condition), with minimum three prior races;
- official timestamped odds history observed by the forecast lock; market namespace remains isolated from ability training.

The upstream machine-learning trainer determines learned coefficients; none are assigned here. \`nar::\` and \`relative::nar::\` features are included in the existing snapshot selector. Schema versions are advanced to distinguish new captures from preserved historic snapshots. Existing archived snapshots and original race facts are unchanged.

## Quality and acceptance requirements
1. Full-field training labels must be verified independently against official race results; training rows must originate from authentic pre-off frozen snapshots.
2. Build a NAR-only, chronologically split training/evaluation cohort in the **existing** mass-training pipeline (see Draft PR #401), keeping jockey/venue/date grouping and the same race denominators.
3. Ablate this feature group against the baseline on paired held-out races, reporting winner-top1, top-three calibration, scenario accuracy, recommended bets and trifecta ROI, with uncertainty/coverage, including missing-source rates. Publish losing periods.
4. Test across all eligible tracks and separately at Kochi, with special evaluation for the final race and for comparable-video-lap coverage. Never assume video measurement is official or directly transferable.
5. Require an independently frozen prospective set, no post-off feature updates, and passing CI before adopting any gains. Official or licensed source permissions must be checked before obtaining new measurements.
6. Integration into active six forecast systems, model deployment, D1 writes, API/UI changes, or rewriting pre-off receipts **is not part of this PR** and must pass the user's production acceptance gate.

## Tests and known limits
- \`tests/test_nar_context_features.py\` exercises pre-off source/time gating, missingness, prior-date separation, JRA/banei isolation, frozen snapshot persistence and market cutoff.
- Current public site AI statistics are self-published, **not** an independent measurement of this model.
- No real source-backed matched-lap, trip-video, track-bias or official odds-history payload has been shown to exist in the current ARVEXQ source data. New features will be sparse or absent until documented authoritative inputs flow through existing contracts.
- New feature calculations alone do not activate predictions; \`arvexq/forecast/engine.py\` remains intentionally inert. Historical win rate / ROI improvement is not demonstrated by unit tests.
