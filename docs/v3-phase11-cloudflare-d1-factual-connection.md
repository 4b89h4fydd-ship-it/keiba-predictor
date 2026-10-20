# ARVEXQ v3 Phase 11 — existing Worker/D1 factual projection

**Draft branch only.** This change does **not** deploy or merge to main.

The existing `GET /api/race/:id` route accepts opt-in `?view=v3-facts`.
It reads the **same existing D1 race_details** through:

1. `readCompressedRace` for existing `arvexqFullPayload` full originals;
2. when absent, `api_preserved.fetch` using the **existing**
   `?view=display` handler (one saved detail read; no new endpoint).

The v3 Worker view rejects bad/cross-circuit IDs and missing race/runner
identity, copies a *strict whitelist* of factual race/runner/history/odds
fields, deduplicates strictly dated runs, omits on/after-race dates,
withholds all results/payouts and former model marks/tickets,
and reports observed prior-run counts as **unverified lifetime coverage**.
It does not rewrite DB, call a new provider, trigger a background refresh,
use post-off ground truth as a pre-race predictor, or calculate an opinion.

A Node integration smoke mocks D1 and exercises both compressed and ordinary
snapshot read routes for JRA/NAR with zero SQL writes, plus 404/422 controls.
CI includes this smoke. The normal `?view=display` and full payload delivery
paths, layout, and Cloudflare deployment remain unchanged.

**Honest limits:** The Worker DTO implements the essential matching factual
screen contract but is not a bit-for-bit Python DTO (and does not decompress
individual sidecar horse histories). It neither certifies complete history,
quote freshness or official roster, nor proves production API readiness.
Live D1 roundtrips and 200-item completion are future acceptance gates.
All 12 JRA/NAR prediction units remain intentionally empty.
