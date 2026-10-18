# ARVEXQ v3 phase 4: observed real archive coverage and API limitation

## Evidence source
The repository's existing `arvexq/ui/static/racecards/YYYY-MM-DD.json`
and matching `saved-snapshots/YYYY-MM-DD.json` manifests. No other
external website, collector or shadow history route was introduced.
A read-only, reproducible command is available:

```sh
python scripts/arvexq_v3_archive_audit.py --days 7 --out arvexq-v3-archive-audit.json
```

### Reconstructed 2026-10-12 through 2026-10-18
- 423 racecard rows match 423 saved-snapshot *manifest entries*.
- JRA 96 races, 1,242 recorded runners; NAR 327 races, 3,415 runners.
- All saved racecards had matching declared fieldSize and saved-snapshot
  manifest horse counts (within the saved evidence inspected).
- Of 7 basic observed runner fields, 29 missing `carriedWeight` records,
  all on 2026-10-12 帯広ば races 01, 02 and 03, with 10, 9 and 10 missing.
- This says **nothing** about the completeness of published official
  races, full history, compressed blob existence/digests, or live data.

### Existing live API audit blocker
GitHub Actions `39139052914`, 2026-10-18T15:07Z, attempted GETs
through the existing `/api/day` read-only path for seven days and received
HTTP 429 on each date. Independent production API total-race and per-runner
history coverage is therefore **unverified**, not assumed zero or full.
Do not add alternate data acquisition routes or further automated API
polling simply to circumvent rate limits. Diagnose and authorize the
existing endpoint's rate budget at the owning infrastructure first.

## Technical safety and proof boundaries
- Structural checks compare only the two local *index files*, not the
  SHA-256 of compressed individual race payloads.
- Every field absence is reported explicitly rather than fabricated;
  the banei carriedWeight gaps remain identifiable by date/race/number.
- No historical race results are used to backfill model inputs.
- The 12 forecast/marks/tickets modules remain empty.
- Existing app display, Cloudflare Worker/D1 and main remain untouched.
- Never claim independent official 100% acquisition from the match
  between two artifacts produced within the same system.

## Next work
Inspect original full snapshots (bounded SHA-256 verified samples)
and reconcile the independent official NAR CSV/JRA evidence with saved
racecard lists. Address the single existing API's 429 budget before
attempting production live readback again.
