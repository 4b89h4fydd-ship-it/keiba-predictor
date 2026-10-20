# ARVEXQ v3 Phase 6 — full repository archive and 429 origin triage

Run (offline, read-only): `python scripts/arvexq_v3_full_archive_audit.py --days 7`

- Every racecard listed in the last seven days is checked against an existing
  content-addressed original envelope, decompressed with the existing bounded
  implementation, SHA-256 verified and race/date/horse identities compared.
- Every embedded `careerArchive` sidecar is verified using the existing
  hash-checked `recover_horse` method. Direct prior-run coverage and
  same/future/invalid history dates are counted; full career completeness
  remains explicitly unverified.
- The existing initial ten-snapshot and twenty spaced-snapshot checks remain.
  Report is uploaded by existing GitHub Actions. No live API requests added.

## Rate limiting evidence
- Historical GitHub Actions job 117709483857, run 39139052914, recorded
  `HTTP Error 429` for all seven archive dates in ~4 seconds.
- No explicit 429 producer in existing `workers/api.mjs` and
  `workers/api_preserved.mjs` was found.
- 429 can originate at edge rate limiting/WAF, third party or other layer.
  Cloudflare's REST API rate limit is separate from a workers.dev route;
  exceeding free Workers daily requests usually reports error 1027.
- A 429 from a detail fetch was previously swallowed into a per-race error
  without stopping remaining dates; the audit now stops at the first
  observed rate limit, including nested per-race failures, and stores safe
  response metadata.
- A live origin attribution still requires Cloudflare dashboard logs or a
  single authorized status-and-headers observation. Do not bypass throttling,
  add new providers, raise request volume or turn off security rules.

No main or production/Cloudflare Worker changes; draft branch only. The
JRA/NAR six-way prediction placeholders remain empty.
