# Phase 20: circuit-neutral observed field counts

The opt-in saved-only factual screen now carries observationSummary, with
observed/missing/invalid counts per basic runner field and per saved prior-run
field, plus missing/invalid/observed-unverified-timestamp odds quote counts.
Denominators are runnerRows for basic/quote fields and observedPriorRuns for
historical cells, not theoretical full career rows. No completeness or market
freshness is certified. Python and Node Worker count the same saved facts;
JRA/NAR parity tests assert matching summaries. Prediction, UI and collectors
are unchanged. No D1 writes or deployment.
