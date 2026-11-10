# ARVEXQ selection ownership

## Current purchase policy (from 2026-11-11)

- Ordinary forecasts and main/graded-race membership remain independent from purchase decisions.
- Popularity rank >=4 is no longer sufficient for a strict purchase. A v26-only signal cannot select production-v9b tickets.
- A purchase must bind to the same forecast model/hash, receipt, active roster and actual wide combinations. Its pre-off evaluation must have independent model/policy validation and fresh observed prices.
- The first registered candidate is wide <=3 points, union hit probability >=70%, stressed expected return >=1.05 after a 10% price decline. These thresholds have NOT passed purchase validation.
- No approved validation artifact currently exists; show purchase conditions pending while retaining ordinary forecasts. Missing evidence is not a model rejection or a losing wager.
- `rewrite/selection/market.py` records append-only market evidence. `scripts/arvexq_selection_odds.py` observes all-circuit win/place and NAR official wide prices, freezes separate candidate outputs, and records purchase decisions per race at T-20..T-15.
- Publication lives in `selection-decisions/YYYY-MM-DD.json`. A confirmed per-race decision is first-write-wins, independent of the daily morning archive and first-race deadline.
- The browser/Node shared `morning/rank_selection.js` verifies v2 purchases. Its old popularity method is retained only for interpreting historical dated records.
- Old `morning-picks/YYYY-MM-DD.json` records remain immutable, including recorded original v26 reasons. Special forecasts retain morning membership independently.

See [implementation, actual comparisons and limitations](verification/selection-priority-fixes-20261111.md).

## Historical morning coordinator

## Morning first-write-wins publication
- `scripts/arvexq_morning_picks.js` is currently the **shared publication coordinator**, not the owner of the above selection decisions. It requires a plausible complete race schedule and at least 80% **individually assessable** cards to avoid sealing a knowingly empty elite slate. It no longer requires all horses' lifetime-history collection to be complete.
- All qualifying selected races and special-forecast memberships are calculated as separate branches and then saved into one date-specific immutable manifest `morning-picks/YYYY-MM-DD.json` before the day's first scheduled off. An existing published manifest always wins; never alter historical membership after results.
- `special` contains every main race (explicit main or 11R fallback), graded races, and Kochi Final, regardless of elite quality or ticket success.
- `selected` includes only candidates whose actual pre-off ticket family and evidence were generated and verifiably captured. Low-confidence triple-order betting may be skipped while a supported unordered main ticket remains.
- First prefetch is at **05:30 JST** (discovery), earliest morning decision at **06:15 JST**, normally retried on the **06:30 JST** run. GitHub Actions cron is best effort, not an exact-time guarantee.
- **Remaining coupling:** selected and special labels still share one daily archive publication deadline, and the large `app.js` still owns core model evaluation and UI integration. This is intentionally documented as not yet a fully independent publisher.

## Tests
- `scripts/arvexq_morning_input_policy_smoke.js`: independent schedule/horse-evidence readiness.
- `scripts/arvexq_morning_selection_cut_smoke.js`: lane types, actual tickets, immutable proof and no daily cap.
- `scripts/arvexq_morning_picks_runner_smoke.js`: first-write-wins morning publication and no after-the-off reconstruction.
- `scripts/arvexq_three_way_bet_smoke.js` and `scripts/arvexq_bet_usability_smoke.js`: independent main/triple/no-axis and partial-career evidence checks.

Previously published dated snapshots, including 2026-10-09, remain immutable historical evidence.
