# ARVEXQ independent pre-off evidence: Cloudflare deployment gates

This is an isolated research data-ingestion endpoint, not a prediction or betting API.

- Path: `POST /api/research/preoff-evidence`.
- Auth: separate secret `FORECAST_CAPTURE_TOKEN` with a 24+ character value; `SYNC_TOKEN` must not be reused.
- Body: `{"snapshot": <unchanged build_mass_feature_snapshot output>, "receipt": <unchanged capture_preoff_features receipt>}`.
- Admission: Worker server time, strict pre-off timestamp, 5-minute ingestion window, same-day race-local post time, full roster parity, SHA-256 integrity, JSON size <950KB.
- Storage: `migrations/0001_forecast_preoff_evidence.sql`, isolated from existing race tables. Immutable insert-only records. Write/update/delete never touches race_details.
- Endpoint does not expose a GET of raw evidence, predictions, marks or ticket suggestions.
- External authentication protects ingestion but does NOT independently verify official race rosters or the source time supplied by the collector. Those need a trusted upstream collector.

## Before activating in production

1. Obtain a dedicated strong secret and provision `FORECAST_CAPTURE_TOKEN` to the Cloudflare Worker. Do not commit it.
2. Back up D1 and review the migration. Apply it explicitly using Wrangler against the correct remote D1 binding and confirm table and triggers. This PR intentionally does **not** automatically migrate D1 on deployment.
3. Deploy the Worker through the existing authorized workflow, confirm normal `/api/day` and `/api/race/:id` responses are unchanged.
4. From a trusted server-side collector, verify the official active roster independently, capture before post, persist locally first, then submit **unchanged** snapshot+receipt with the secret.
5. Verify D1 row append, idempotency, no update/delete, rejection after post, and absence of legacy marks/tickets.
6. Preserve immutable labels separately and evaluate unknown future races before enabling any public predictions.

## Failure behavior

If migration or token is absent, ingestion must fail closed. No fallback to old prediction or a forged after-the-fact capture. A local SQLite capture is not evidence of Cloudflare D1 availability. Hash checks establish self-consistency, not that a third-party data source was truthful at the timestamp.

No production 80% hit-rate claim is made.
