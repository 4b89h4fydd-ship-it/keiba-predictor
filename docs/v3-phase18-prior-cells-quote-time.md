# Phase 18: saved prior-run cells and quote-time classification

JRA/NAR opt-in factual readiness independently records `pastFieldStates` for
each observed prior race (track/distance/finish/last3f) and `quoteTimeState`.
Prior-run cells are `observed`, `missing`, or `invalid`. Quote time is
`observed-unverified-timestamp`, `missing`, or `invalid` and is selected
only from saved runner oddsUpdatedAt/oddsTimestamp, not race start time.
An observed timestamp is **not** independently verified to be fresh.
This does not assert all historical races are available. No collector change,
UI modification, D1 write, predictions, main merge, or deployment.
