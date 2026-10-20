# Phase 21: read-only observation count reconciliation

The Python v3 factual display projection now rejects coverage count totals
that disagree with independent runner, career-history or saved quote rows.
It also rejects aggregate oddsFields state counts that do not equal the
per-runner win/place/popularity field states. Counts must be exact integers
(bool is not accepted). The computed observationSummary remains derived from
validated runner evidence, including all saved historical runs, never just
the five displayed recent races. No assertion of complete career histories,
verified roster or market freshness is made. JRA and NAR regression tests
tamper with every monitored aggregate and assert fail-closed behavior.
No collector, UI, prediction, main merge or deployment changes.
