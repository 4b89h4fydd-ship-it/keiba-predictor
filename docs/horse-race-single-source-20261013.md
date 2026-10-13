# ARVEXQ horse data / presentation ownership

Only the current application code in `app.py`, `arvexq/`, `workers/` and `arvexq/ui/static/` owns runtime behavior.

## Racecard source of truth
1. The verified dated factual card `/racecards/YYYY-MM-DD.json` may paint early if available. Its horse identities are validated and it is not betting evidence.
2. The D1 `GET /api/race/:id?view=display` is the single live *full detail* reader; the current application merges verified identity, odds and context without clearing good fields.
3. Only after no runners can be displayed does `GET /api/racecard/:id` supply a compact D1 card. The static dated archive inside the card helper is the same immutable source as step 1, not an additional outside data provider.
4. Saved pre-race snapshots must never replace current race runners while opening a race. They remain immutable evidence for audit and results.
5. Device race/detail/full-bundle caches use the versioned `horse-race-source-v362` schema. Older dynamic caches are removed when upgrading; user forecasts and receipts are never evicted.

## Code ownership and updates
The historic `scripts/arvexq_patch_*`, `scripts/arvexq_fix_*` single-use patch generators and GitHub Actions that automatically commit those generators have been retired. Update the current source directly via reviewed, validated PRs. The `ARVEXQ Race Open Integrity (read-only)` workflow checks the new loader but cannot rewrite `main`.

The separate official data prefetch, history, result, and snapshot safety jobs continue to publish *immutable race data*; they do not patch UI logic. Never delete a race's pre-off original, recorded ticket, observed result, or backup merely because an older implementation used it.

Prediction weighting and the `◎` scoring equation are not modified by this cleanup.
