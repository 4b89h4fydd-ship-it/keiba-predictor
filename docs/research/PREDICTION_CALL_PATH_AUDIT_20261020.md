# ARVEXQ prediction path audit — 2026-10-20

Scope: read-only tracing and classification of existing paths. No new forecasting route, scoring formula or data feed.

## Confirmed implementation edges
1. `app.py` imports `build_prediction` from `arvexq.forecast.engine` as `_build_prerace_prediction` (line 809 at inspection). `arvexq/forecast/engine.py` documents the rejected assistant baseline as retired and currently returns `None`. **This import is not evidence of an active predictor.** Caller execution still requires auditing.
2. `arvexq/forecast/publication.py` forwards to `arvexq.components.item_126.publication`; the implementation strips retired derived predictions/marks/tickets and marks public projection `predictionStatus=disabled`. This is a compatibility alias and not a separate engine.
3. Client `arvexq/components/shared_ui/0131_predict.js` delegates to `window.ARVEXQProductionPrediction.build(r)`. Its defining script, registration and live call graph are not yet proven by this audit; do not infer another active engine.
4. `arvexq/components/item_185/ui/prediction_frame.js`, `item_186/ui/mark_frame.js`, and `item_187/ui/ticket_frame.js` are read-only display surfaces, not independent ranking algorithms.
5. `arvexq/v3/prediction/status.py` returns `not-implemented` for all six JRA/NAR units. Sampled `jra/ability.py` returns `None`. Do not attach unapproved models to these interfaces.
6. `arvexq/research/stage64/pipeline.py` reuses stage63 `ability`, `running_style`, `pace`, and `probability` functions; it has separate stage64 research `marks` and `tickets` role selectors. It explicitly returns `productionEligible=False`. Stage63 `experiment.py` is a NAR-only offline experiment, not a validated production alternative.

## Critical clarification
Multiple module names and research candidates exist. That does **not** prove multiple production forecast engines run concurrently. An end-to-end runtime caller trace (server registration, actual public API projection, loaded client bundles) is **not completed**.

## Verified corrections
The unauthorized `arvexq/research/stage65/` and `tests/test_stage64_win_focus.py` additions were reverted in previous commits. No path resurrection.

## Required next audit before any runtime code change
- Inspect all `_build_prerace_prediction` usages and `ARVEXQProductionPrediction` definition/callers, then record exact import/bundle/API edges.
- Inspect which active API endpoints call `public_race` and their race-detail projection.
- Confirm previously authorized approved model identity; absence of approval is **not** permission to install a replacement.
- Run regression/CI checks against any user-approved targeted change; keep JRA/NAR segregated.
- Preserve all source data, pre-off receipts and prior research; no main merge or deploy.

No claim of production prediction activation, end-to-end routing completeness or independently verified future-race hit rate is made.
