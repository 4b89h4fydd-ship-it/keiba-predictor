# ARVEXQ v3 phase 10 — existing FastAPI route connected to factual-only units

- Existing `GET /api/v1/race/{race_id}?view=v3-facts` is now a separate
  **opt-in representation** of the same existing route, using the saved
  prepared/race-store resolver. No new endpoint/provider/external network.
- No fallback to a second collector, refresh queue, prefetch run or write.
  Cache miss returns 404 instead of initiating a background update.
- Stored race identity/circuit are verified. Observed entries/history/odds
  are composed by the previously separated JRA/NAR modules.
- This view always withholds original postrace results, payouts, archived
  marks, predictions and saved tickets; all 12 new prediction units stay
  empty. It never promotes unverified archived history to 100% complete.
- Calls to the existing endpoint without `view=v3-facts` continue to return
  the previous UI format and retain their existing refresh behavior.
- The branch already contains both `oddsFields` (detailed source/date/market
  observation) and `quoteFields` (individual raw quotes); the two
  contracts remain distinct, with no duplicate dictionary key.
- This is **local FastAPI** wiring, not Cloudflare Worker `/api/race/:id`
  (which remains the canonical deployed external detail owner). No D1
  schema, app CSS, mobile UI layout, or Cloudflare deploy changes.
- Full live FastAPI request/response and Cloudflare integration need further
  production evidence. This PR remains draft/unmerged.
