# ARVEXQ v3 phase 2 — circuit-owned factual observation domains

Not a production launch and not a completion claim for the original 200-item plan.

## Delivered
The existing JRA/NAR ingestion sources stay authoritative. Existing snapshots
are read through ten independent, testable adapters:
- `jra/race.py` and `nar/race.py`: race identity, timing, ground facts.
- `jra/entries.py` and `nar/entries.py`: runner field observations only.
- `jra/history.py` and `nar/history.py`: strictly prior history by runner
  row, never joining horses on name or number; completeness remains unverified.
- `jra/odds.py` and `nar/odds.py`: observed prices/popularity, no invented
  quote or inferred wagering value.
- `jra/results.py` and `nar/results.py`: observed finishers/payouts,
  distinctly NOT an official result-confirmation authority.

`observed_fields.py` owns tiny shared field contracts but each circuit has
its own adapter entrypoint. `circuit_review.py` supplies a compact coverage
summary. The single existing `prepare_race_detail` pipeline attaches
`v3CircuitCoverage`; no new network, database, API endpoint, or UI asset.

## Invariants
1. Never infer unknown circuit, promote archived marks or bet decisions,
   or introduce a second history fetching path.
2. No v3 prediction logic exists. The 12 prediction placeholders stay inert.
3. Missing prices, runner facts, histories and results remain missing.
4. Histories on race day or later are excluded from pre-race history views.
5. Race snapshots/results/preoff original receipts are not overwritten.
6. Fail closed when a race ID contradicts the circuit.
7. Central racing and local racing are isolated at the adapter boundary.

## Next verification gates
- Prove live per-field coverage with actual JRA/NAR data and source timestamps.
- Map every remaining item in the original 200-item independence ledger.
- Independently validate complete roster and historical start coverage.
- Integrate the interface into the actual D1/API only after readback evidence.
- Leave marks/forecast/betting empty until a separate approved method arrives.

## Rollout
Development PR only. No main merge, Cloudflare deployment or D1 mutation.
