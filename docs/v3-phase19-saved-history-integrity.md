# Phase 19: observed history display integrity

Fix the Phase 18 parity fixture: an older career finish remains observed after
same-day merging with a complementary recentRaces track field.
Validate full per-runner prior-run count against untruncated history.
Fail closed if runnerReadiness pastFieldStates have inconsistent length,
date identity, keys or observed/missing/invalid status.
Only bounded quoteTimeState vocabulary is accepted. No timestamps are
assumed fresh or official; timestamp provenance is owned by quoteFields.
JRA and NAR regression cases cover the tampering scenarios.
No prediction, collector, UI or existing storage changes.
