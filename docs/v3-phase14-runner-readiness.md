# Phase 14 — per-runner factual history/odds readiness (draft only)

Both JRA and NAR have independently importable saved-only `runner_readiness`
readers. Each runner publishes `rows[].readiness` in the Python FastAPI
opt-in and the Cloudflare Worker opt-in. The fields are `history`, total
`observedPriorRunCount`, `odds`, independently classified `win`/`place`/
`popularity` states, and explicit false completeness/freshness claims.

Missing prior runs are **unknown history, not a proven debut**. Observed
prices do **not** prove market freshness or a current quote. Neither path
builds probabilities, marks, predictions or tickets. No UI/layout, main,
production deployment, alternate fetch or database write is added.

The Python screen readiness now counts all observed prior runs, rather than
the five display rows. The Worker coalesces same-calendar-date saved history
rows so one source overlap does not inflate observed starts. A full source
field-by-field parity audit and live D1 readback remain unverified.
