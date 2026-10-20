# ARVEXQ v3 phase 3 — read-only storage/cache/API/screen separation

Scope: independent factual **interfaces**, not new data providers, HTTP endpoints,
storage writers, caches, or changes to existing screen layout.

## Implemented
- `transport/storage.py`: calls the existing getter once with race ID and validates
  returned snapshot/circuit; never writes to the store.
- `transport/cache.py`: pure v3 namespaced key + caller-supplied timestamp/TTL
  classifier. Does not create a second cache or an eviction route.
- `transport/api.py`: strict observed-only response DTO composed from existing
  circuit readers. Result and payout are withheld by default so a pre-race
  consumer never accidentally receives post-race labels.
- `transport/display.py`: render-neutral per-runner DTO with observed history
  and quote fields; refuses mismatched runner/history/odds rather than joining
  by horse name or silently moving history to another number.
- `transport/boundary.py`: compact read-boundary state in
  `prepare_race_detail` under `v3ReadBoundary`; no extra storage/API reads.

## Explicit limitations
This implementation does NOT deploy a v3 API HTTP route, rewire mobile PWA
rendering or certify result finality. Existing production is left unchanged.
Cached saved race observations are NOT proof of pre-race availability; any later
live forecast input must be separately time-bounded. No expiry is inferred
without an explicit caller-provided TTL and clock.

## Preservation
No modification to existing SQLite/D1 schema, source registry, pre-off sealed
originals, existing PWA screen code, `cloudflare` branch, or main. All JRA/NAR
ability / running style / pace / probability / marks / tickets remain empty.

## Remaining work
Verify actual data across JRA/NAR race dates, identity, quote times, missing
history, pre/post evidence provenance, API delivery, and browser readback before
wiring v3 DTOs into the real user interface. Maintain original 200-item ledger
without counting the entire system as complete.
