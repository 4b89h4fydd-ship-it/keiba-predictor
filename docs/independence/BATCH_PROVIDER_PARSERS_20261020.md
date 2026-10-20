# Provider parser extraction — 2026-10-20 JST

PR #367 development branch only. No merge/deploy. Fixed inventory remains 200; this batch does not certify any additional item as production complete.

## Actual code change

Removed the remaining inline NAR market DOM parser, NAR official result DOM parser, JRA official result DOM parser and shared payout DOM parser from `app.py`. They now live in `arvexq/ingest/nar_odds.py`, `nar_result.py`, `jra_result.py` and `payouts.py`. Existing HTTP acquisition wrappers invoke the extracted implementations. Existing URLs, source order, timeouts, retries, cache keys/TTL, result payloads and persisted stores are preserved. Parsers receive explicit pure callbacks and do not acquire data or write stores. No UI or forecast calculation changed.

Affected inventory: #020 JRA official parser, #021 NAR official parser, #064 NAR odds, #076–083 observed payouts. These are **partial**, not complete: the eight payout kinds still share one table decoder; field-level parser ownership, complete historical source coverage and the storage/cache/API/UI/live gates are not certified. Ledger source state for the nine previously unstarted responsibilities becomes 解析済, not 分離済 or 本番検証済.

## Verification

- 13 migration comparisons against functions at baseline commit `b58f39ac1111a14dde6aa0dc165dca12330547f2` (before this batch): NAR with/without sectional column and three status variants, header/positional market pages with/without scratches, JRA result pages with three status variants: exact parsed output equality.
- New `tests/test_provider_parser_boundaries.py`: 17 offline contracts covering transport isolation, unchanged official source URL, source immutability, missing podium/sectionals, tied market ranks, scratches, eight payout kinds/aliases, duplicate removal, and JRA strict fetch-error handling. Added to Independent Components CI.
- Initial full suite: 1,130 passed, 3 skipped, 37 subtests passed; 3 failed because existing archive-window tests referenced missing `2026-10-19.json` files. Those three contracts now copy actual unchanged Oct 16/18 archive pairs to exercise the same Oct 17 calendar gap. No saved originals created or modified; no tests skipped to hide the missing file.
- Resumed as part of the 200-box batch: full Python suite **1,167 passed**, 37 subtests passed; 17 provider-boundary contracts passed. See `STRUCTURAL_200_BOXES_20261020.md` for the final migration scope. Parser implementations now live under boxes 020, 021, 064 and 076; former import paths are compatibility shims.

## Remaining boundary

No new live provider requests, D1 mutations, schema migration, main merge or deployment. All twelve v3 prediction units remain inert. Historical parser behaviors (including legacy sentinels/fallbacks) are preserved during this extraction; this batch is not a factual-completeness or zero-fabrication certification of every legacy result field.
