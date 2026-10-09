# ARVEXQ morning selection ownership

- `morning/selection_cut.js`: Takes every race that passed `strictSelectedRaceProfile` and sorts chronologically. **No per-circuit cap of one**, no best-minus-two cut. Strict prediction evidence/quality gates remain intact in `app.js`.
- `scripts/arvexq_morning_picks.js`: Reads the prepared full-day card, requires every race to have a basic 3+ runner card, and freezes when at least 80% of diagnoses are ready. Every race receives an immutable assessed/unassessed flag; missing data is never called a negative model judgment.
- The fixed `morning-picks/YYYY-MM-DD.json` is published only before the first off. Subsequent re-fetches or updates must not change existing membership. An already published file always wins.
- Earliest full prefetch starts at **05:30 JST** (discovery only); earliest on-day morning decision is **06:15 JST** and is normally attempted at the **06:30 JST** run. Other scheduled runs at 07:30 and 08:30 provide retries if the morning input was incomplete. GitHub Actions cron is best effort; no exact publication-time guarantee.
- `special` marks all main races (explicit or track 11R fallback), graded races and Kochi Final as morning-fixed special forecasts; these are separate from genuinely selected 厳選 races.
- The published Oct 9 2026 34-race snapshot was fixed at 09:07:59 JST, with one selected race. Never replace it with revised historical picks.
