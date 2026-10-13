# ARVEXQ morning selection ownership

## Independent processing branches
- **Data acquisition (Python)**: `arvexq/ingest/` collects and merges observed horse careers. `arvexq/prediction/career_readiness.py` reports full-career completeness; this is not a global purchase veto.
- **Individual morning-card readiness (Node)**: `arvexq/pipeline/morning_input_policy.js` validates the race schedule and checks observable per-race horse history separately. A missing `careerReady` flag does not by itself make a race unanalyzable. Genuinely sparse cards are marked **unassessed**, never **not selected** on model grounds.
- **Selected races (browser/Node shared)**: `arvexq/ui/static/morning/selected_race_pipeline.js` obtains model and independent ticket decisions via injected interfaces. `ticket_lane_classifier.js` classifies place/winner/longshot types. `selection_cut.js` retains only `的中重視型` tickets with internal score >=80 and real morning evidence. No daily cap; 80 points is not 80% hit probability. Historical locked selections are immutable and do not enter the current elite display if they miss the threshold.
- **Special forecasts (browser/Node shared)**: `arvexq/ui/static/morning/special_selection.js` determines main/graded/Kochi-Final membership from schedule metadata only. It does not read lifetime-history completeness or ask the betting engine whether a wager is recommended.
- **Buying (browser)**: `arvexq/ui/static/betting/bet_readiness.js` checks purchasable reference evidence. `main_strategy.js`, `no_axis_strategy.js`, `trifecta_strategy.js`, `insurance_strategy.js` separately determine main, no-axis, triple-order, and insurance outcomes. `three_way_engine.js` assembles ticket families. Triple-order requires stronger source-backed data than unordered tickets.
- **Frozen evidence (browser/Node shared)**: `morning/frozen_ticket_evidence.js` validates actual pre-off horse numbers/marks/ticket combinations; a public elite selection must have real saved ticket evidence.

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
