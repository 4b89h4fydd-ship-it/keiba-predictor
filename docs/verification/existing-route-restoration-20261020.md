# Existing route restoration — 2026-10-20

User scope: inspect existing paths, restore divergences to the established path, repair it, and remove the divergent implementation. No main merge, deployment or production D1 writes.

## Baselines and concurrency

- main: `9096e47b7c5ddcc6fe9310149ac2df1132078cf9`
- isolated PR #374: `e3485d7d0a738116cb55493475a8c72d7a54b0c8`
- Work branched from #374 without changing its branch or any Stage1–5 branch. All 33 open PR file lists were checked; shared files are changed only on this new isolated branch. A filename overlap is not permission to overwrite another branch.
- Data plugin index was consulted. This is source-code repair, not a quantitative analytics report; GitHub code and #371 decisions control the route classification.

## Reviewed boundaries

| Boundary | Existing source / owner | Finding and action |
| --- | --- | --- |
| Central acquisition | `legacy_bridge.register_legacy_sources` → JRA adapters / established netkeiba adapter | Keep existing providers, identity and circuit guards. Source discovery catalog is not an enabled provider registry. |
| Local acquisition | same registrar → NAR store, prior official results, local NarSync CSV archives | Keep the established archive path and identity guards; do not classify different official file formats as rogue providers. |
| Pre-off history completion | `freeze_predictions.recover_prior_history_before_post` → isolated rescue → existing registrar | Rescue still imported deleted `authorized_feeds`; restored to `register_legacy_sources(vars(app))`, using normal application callbacks and archive registration. No feed URL configuration introduced. |
| Persistence | existing sync protection, SQLite stores, compressed D1 snapshots | Preserve original receipts, revision rows and backup export. No database deletion or schema operation. |
| Cloudflare detail read | `workers/api.mjs` → item 173 → compressed snapshot / existing API reader | Keep the same canonical `/api/race/:id` route and its storage formats. These representations are not new providers. |
| Live display | item 193 `fetchEdgeRace` → `/api/race/:id?view=display` | Removed parallel `/api/forecast-revisions/:id` request and candidate response merge. An invalid candidate response can no longer reject an otherwise valid factual detail. |
| Candidate API | item 173 → `workers/api_forecast_revisions.mjs` | Deleted candidate reader, migration, publisher and pointer updater implementation. Retired URL prefix returns 410 before accessing D1; unknown URL fallback previously returned 200 service metadata, so simply deleting dispatch would hide retirement. |
| Compact card / dated factual archive | `fetchRacecardOnly` and existing static dated racecards | Retained as documented compact factual fallback, not an independent forecast or provider. |
| Odds | existing live odds module → canonical odds fallback | Kept existing odds behavior; no source priority or fetch URL change. |
| Forecast, marks, tickets | production UI modules display validated pre-off receipts; reserved v3 units remain inert | No model installed or re-enabled. #374 already removes `new_forecast` generation route; this delta closes its remaining live transport dependency. |
| Research | stage63/stage64 and existing archived research | Keep source records and research. An offline experiment is not by itself evidence of an active production route. |

## Reproducible static inventory

`existing-route-inventory-20261020.json` records a source sweep over app.py, arvexq, workers, scripts and workflows: 1,403 source files, 123 Python HTTP decorator registrations and 41 targeted route references at the time of the scan. This is an inventory, not proof that every branch was dynamically executed. Some decorators are assembled into the application through existing component installers.

## Validation

- Targeted Python suite: 29 passed, including historical receipt preservation, source isolation, pre-off rescue, UI assembly and Worker ownership.
- Node: canonical reader success/error behavior passes; retired API GET/POST/OPTIONS against all three endpoint forms returns 410 without any D1 access; saved original marks/bets remain unchanged.
- 200-component audit: errors=[], definitionParity=true. Allocation remains 61 migrated modules, 82 shared contexts, 28 UI fragments, 29 reserved.
- Static build succeeds (v330, 89 files); generated app.js exactly follows canonical component assembly.
- Full local Python suite: 1,351 passed, 1 skipped, 45 subtests passed (12 existing deprecation warnings).
- Mobile browser execution was attempted but blocked locally: Playwright Chromium executable is not installed. This is not reported as a browser pass. The updated browser regression asserts zero candidate-API requests.

## Explicit remaining limits

No production acquisition, D1→API→UI readback or deployment was performed. Missing career histories, SQLite lock contention and Morioka missing results are not proven repaired by this change. All-path dynamic verification and production restoration remain unverified; do not report the entire request complete from a source sweep.

The offline `scripts/arvexq_learned_scenario_evaluation.py` still references the removed candidate. No workflow or caller was found in the searched source. Its research provenance must be distinguished from a production path; this change does not erase existing research to make an import inventory appear clean.
