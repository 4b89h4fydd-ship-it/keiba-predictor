# ARVEXQ v3: data boundary + empty six prediction components

This is the first scoped implementation step, not completion of the existing
200-item independence ledger. No production model has been approved.

## Scope
- Keep the **existing** JRA/NAR provider registry, acquisition jobs, SQLite/D1
  snapshots and authoritative race-detail API. Do not add an alternate fetcher.
- Data boundary `arvexq/v3/data/quality.py` audits observations and coverage
  independently of scores; *not* evidence that lifetime history is complete.
- Storage adapter `data/storage.py` only reads an injected **existing** getter
  and checks that the saved race ID matches the requested ID. No DB writes.
- `data/display.py` projects raw observed fields, strictly earlier career
  history, confirmed results, and a quality summary. It does **not** include
  old predictions, marks, or tickets.
- Six empty units under each of `prediction/jra` and `prediction/nar`:
  ability / running_style / pace / probability / marks / tickets.
- `prediction/status.py` explicitly returns not-implemented with null forecast,
  marks and tickets. No fallback to retired scoring paths.
- Read-only factual summary `v3DataStatus` is added by the existing
  `prepare_race_detail` orchestration. Existing UI and layouts unchanged.
  **This does not turn on any new forecast or change historical seals.**

## Correctness gates
- Validate circuit and race ID; unknown is not silently central or local.
- Keep true missing facts missing, and report duplicate/invalid runner numbers.
- Flag target/same-day and future history; never pass it into a past-runs view.
- Do not claim complete lifetime history from observed prior races.
- No display projection may expose pre-off archived bets or former marks.
- Full Python regression and PWA smoke must pass before any production merge.

## Later steps (not yet done)
- Extraction, persistence and display owner-by-owner mapping of all 200 items.
- Verified cross-runtime prefetch/D1/API readback and all-race coverage.
- User-approved new prediction methodology, independent numerical calibration,
  mark roles and ticket generation; these must remain empty in this change.
- Production rollout: not in scope.

## Safety
Do not delete D1 records, existing immutable pre-off originals, frozen tickets,
results or backups. Do not merge the separate cloudflare API branch into main.
