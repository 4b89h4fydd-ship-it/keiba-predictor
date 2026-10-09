# ARVEXQ Stability Gate — 2026-10-10

## Verified in repository
- app.py reduced from 1,060,034 to 364,324 bytes; pure functions separated.
- Latest full CI validation succeeded at bd906f5f.
- The pre-race morning prediction original, official revision chain, and historical bets must remain immutable.
- Full observed career must be kept; no fabricated starts or future outcomes.

## Blocking operational issue
Cloudflare D1 rejected writes with D1_ERROR: Exceeded maximum DB size and also Worker 1102 resource failures.
Cloudflare D1 Free limit: 500 MB/database; Paid limit: 10 GB/database; maximum value/row: 2,000,000 bytes. Production plan and current file size remain unverified.
API Worker storage code is not in the keiba-predictor repository, preventing server-side R2 migration or D1 sharding from this repo.

## Protections shipped
- scripts/arvexq_d1_capacity_guard.py: abort repeated writes on known permanent D1 capacity and Worker errors; only bounded transient retries.
- .github/workflows/arvexq-prefetch.yml, arvexq-sync.yml: use guard and preserve post-write seal verification.
- scripts/arvexq_sync_batches.py: flags details over 1.8 MB as potential D1 one-row size limit risks.
- scripts/arvexq_d1_storage_audit.py: read-only Cloudflare D1 file-size request. Existing deploy token returned HTTP 401.
- .github/workflows/arvexq-d1-storage-audit.yml: manual until D1 Read token is configured as CLOUDFLARE_D1_READ_TOKEN.
- tests/test_d1_capacity_guard.py and tests/test_d1_storage_audit.py cover safety without network calls.

## Recovery gate (no deletion)
1. Connect an authorized D1 Read-only token; inspect real database size and Workers tier.
2. Export and verify backup before any cleanup or schema change. Preserve morning snapshots, revisions, bets, result history, and horse starts.
3. Access original kraiz-api Worker source; inspect large tables and row size. Increasing the plan alone cannot solve a 2MB individual value.
4. Move oversized immutable career originals losslessly to R2 or sharded D1 with content-hash verification; D1 should hold compact indexed queryable fields.
5. Only after revalidation of all cards, pre-off snapshots, payouts and post-write seals, re-enable unrestricted sync.

## Not yet proved
- Production full prefetch success, complete per-horse career coverage or D1 capacity recovery.
- Any improvement in the actual held-out pre-off ◎ place rate.
- Elimination of Worker 1102 and API 500/503.
