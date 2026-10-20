# ARVEXQ v3 phase 9 — independent market quote fields

JRA and NAR have separate read-only modules for **win odds, place odds,
popularity, and dedicated odds observation timestamp** (8 units total).
The one existing saved race input remains the sole source. No external
odds providers or parallel fetchers are added; no prediction is calculated.

The price timestamp is observed ONLY if explicitly provided by a runner's
`oddsUpdatedAt` or `oddsTimestamp`, never guessed from the race update,
clock time, or cache TTL. A timestamp is not certified as timely; freshness
stays unknown. Missing/invalid odds stay missing or invalid. A provider's
raw place-odds range remains raw until its schema is verified.

`factual_response` and `factual_screen` gain `oddsFields` read-only
DTOs, separate from the original compatible `odds` property. No
production Worker HTTP route or existing UI is modified.

This is limited to saved-fact projections, not upstream parser/provider,
storage/update, live quote timestamp verification or historical source
coverage. The independence ledger #59-69 is not automatically completed.
Forecast/marks/tickets remain empty. Draft PR only.
