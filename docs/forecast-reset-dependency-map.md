# Forecast reset dependency map (2026-10-16)

Verified against branch feature/forecast-reset-20261016.

- API: app.py::_precompute_detail_metrics calls _rank_evaluations. The function is installed by arvexq/domain/legacy_evaluation.py::install_evaluation_core, delegating to arvexq/prediction/final_marks.py::apply_core_marks and then observed_model.py::apply_observed_marks.
- Pre-off server freeze: scripts/arvexq_freeze_predictions.py calls apply_core_marks, app.py::_build_prerace_prediction, then prerace_archive.py::seal_detail.
- The API prediction audit in app.py::_build_prerace_prediction still checks observed_model.model_version and narModelEvidence (Mineta/margin), so changing final_marks alone breaks freezing.
- Browser: arvexq/ui/static/app.js::predict calls assignPredictionMarks -> assignObservedPredictionMarks. buildAiBetPlan calls buildObservedBetPlan. The browser independently computes ranks, role probabilities and combinations.
- Rendering: arvexq/ui/static/betting/bet_view.js renders buildAiBetPlan output. build_static.py compiles app.js into app-v330.js for index.html.
- Historical protection: prerace_archive.py preserves preRacePrediction/preRaceBet; arvexq/infra/race_stores.py preserves earlier sealed snapshots; app.js::applyFrozenMarks and frozenAiBetForRace display pre-off receipts.
- Risk: app.js::buildAiBetPlan currently generates post-race revised tickets. These must remain separate from original pre-off records and never be counted as prospective hits.
- Candidate new_forecast.py is not wired to either runtime and remains uncalibrated. Do not deploy it until both paths are replaced and tested.

Replacement must update backend ranking, server audit/freeze, browser prediction, browser betting and historical display together. Source inspection does not verify live D1 backups or production deployment.
