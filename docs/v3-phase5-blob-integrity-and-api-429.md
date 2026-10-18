# ARVEXQ v3 phase 5 — offline source blob SHA-256 sample / 429 audit stop

## Preserved source
The v3 audit uses only existing `arvexq/ui/static/saved-snapshots` gzip
envelopes + racecards + manifests. No additional data source, scrape, race
API request, HTTP endpoint, DB write, Cloudflare configuration change or
forecast calculation is introduced.

## Offline digest verification
- Daily sorted race IDs are sampled deterministically at most twice per
  circuit; dates with no circuit racing are not fabricated.
- For each sample, verify individual JSON file existence, envelope version,
  sha256/size, bounded base64+gzip reconstruction, full original-byte
  SHA-256, race/date/circuit and card-vs-original horse identities.
- Emit only race IDs, digest metadata and error codes; the historical
  protected mark/bet original remains in source, unmodified.
- This is *bounded sampling*, not proof that all 423 underlying blobs
  decode correctly, nor that all runs/horses match JRA/NAR publications.
- Runtime should never treat manifest-only matches as hash verification.
- Run read-only: `python scripts/arvexq_v3_blob_digest_audit.py --days 7 --per-circuit 2`.

## Existing API HTTP 429 evidence and guard
The GitHub Factual Data Audit action run 39139052914 on 2026-10-18T15:07Z
received HTTP 429 for all seven attempted dates 2026-10-12..18.
The existing `get_json` requester retries temporary errors (including 429),
then `arvexq_fact_data_audit.py` used to continue to the next date.
Now the audit stops subsequent date requests when **HTTP 429 reaches
the caller**, clearly recording `api-http-429` once and skipped dates
as unverified. No bypass, alternate upstream or retry increase.

Source code inspection of `workers/api.mjs` and
`workers/api_preserved.mjs` found no explicit 429 emitter. That does
not locate the true actor; an edge rate-limit, security rule, upstream
policy or some other handler needs response-header and operator telemetry
to differentiate. Do not assert this is resolved without those logs.

## Operational next step (operator investigation only)
Review Cloudflare requests/logs for that timestamp and hostname,
rule/action, response status by edge/origin, Retry-After and
rate-limit telemetry. Check scheduled concurrency and sanctioned API
request budget, respecting original single-route constraint.
Do not disable protective controls blindly.
No further production live read is scheduled by this PR.

## Invariants
JRA/NAR original data, D1/SQLite, immutably frozen pre-off snapshots and
legacy archive are unchanged. New ability/style/pace/probability/marks/
tickets units remain empty. This change is draft-only; main and UI
presentation stay unchanged.
