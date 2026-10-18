# ARVEXQ v3 phase 7 — evidence-only runner gaps

The seven-day repository originals have already passed SHA-256/identity checks
and 3,600 saved career sidecars decoded successfully. This addition records,
at individual race/horse granularity, WHY a horse currently has **no observed
prior race**, without guessing debut status.

## Diagnostic categories
- `reported-prior-starts-not-observed`: an as-of-race-date, non-conflicted
  source start count is positive yet no prior starts are present. This is
  a concrete incomplete-history candidate.
- `dated-source-reports-zero-starts`: trusted date-bound source says zero,
  but not absolute proof of first start.
- `debut-race-without-dated-start-evidence`: race title contains 新馬,
  only circumstantial context, NOT official debut confirmation.
- `no-prior-runs-unverified`: no reliable date-bound evidence; **never**
  automatically classify as debut.

Review every case in `runnerEvidenceTriage.noPriorRunCases` in the full
archive audit artifact. There is no backfill, merge by horse name, new
provider, or alternate data acquisition.

## 2026-10-12 帯広ば 1–3R missing carriedWeight cases
Compare the saved racecard and its SHA-256 verified original:
- `saved-original-has-carriedWeight-card-blank`: likely presentation
  boundary issue; raw original observed value retained as evidence.
- `saved-original-other-weight-key-card-blank`: possible field mapping;
  do NOT equate a generic weight with banei carried weight until confirmed.
- `saved-original-and-card-both-blank`: unknown at original storage,
  needs provenance inspection through the single established acquisition.
No values are invented. The audit leaves immutable original data untouched.

## Reproduce
```sh
python scripts/arvexq_v3_full_archive_audit.py --days 7 --out arvexq-v3-full-archive-audit.json
```

Output is the existing archive audit artifact with the additional
`runnerEvidenceTriage` section, including track/age/name/number references
and source-evidence limitations. No frontend changes. Existing 12 prediction
modules remain empty and PR is draft, unmerged.
