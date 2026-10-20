# ARVEXQ v3 phase 9 — JRA/NAR observed odds facts

Physically separate **14** independent reader entrypoints: per circuit,
7 modules `win / place / popularity / timestamp / source / delta / missing`.
Only already-saved, canonical race details are passed to them. No new
provider, network route, D1 mutation, odds auto-refresh, calculated return,
probability prediction, or wager recommendation.

- Win, place and popularity are **observed only**. Missing/invalid/observed
  are distinct; negative, zero, NaN and malformed prices are invalid, not
  synthetic odds. Place ranges are validated using the existing independent
  place-odds parser but retained as source strings.
- The delta field only describes a delta value already present in the saved
  snapshot, and **does not recalculate two market observations**.
- `oddsUpdatedAt` is often only local clock time. A clock time without
  date/time zone is **NOT** a certified pre-off or fresh market observation.
  `oddsSource`/`oddsType` labels are claims stored with original data,
  not independently validated source provenance.
- The existing v3 API and screen **data contracts**, not deployed HTTP/UI,
  now include the independent `oddsFields` DTO. JRA/NAR identity guards,
  deep-copy behavior, results embargo and null model/marks/tickets remain.
- Ledger requirements 59-69 have additional read-only separation evidence;
  not enough for main merge, acquisition source ownership, storage roundtrip
  or complete ledger status. Do not promote them prematurely.
