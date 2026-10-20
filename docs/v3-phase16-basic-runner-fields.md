# Phase 16: independent basic runner-cell status

The saved-only, opt-in Python and Worker factual screen contracts now carry
`rows[].readiness.basicFields` for four unmodified runner fields:
`name`, `jockey`, `trainer`, `carriedWeight`.
Each is independently labeled `observed`, `missing`, or `invalid`.
This is an observation status, **not** a statement of official completeness.
Per-runner history and odds statuses remain separate and never enable a
forecast. JRA and NAR cross-runtime parity tests compare identical saved input.
No extra acquisition route, schema write, existing UI change, prediction,
main merge, or deployment.
