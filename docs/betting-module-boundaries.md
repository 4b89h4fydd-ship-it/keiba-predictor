# Betting module boundaries (ARVEXQ v346)

| Module | Responsibility |
|---|---|
| `arvexq/ui/static/betting/three_way_engine.js` | Conditional role ordering plus main / 3連単 challenge / insurance decisions, independent of UI and persistence |
| `arvexq/ui/static/betting/bet_view.js` | Display of three ticket groups, preserved earlier fixed tickets, explanations and points |
| `arvexq/ui/static/betting/bet_ui.css` | Betting-only responsive styles; no homepage changes |
| `arvexq/backtest/ticket_metrics.py` | Official dividend interpretation, observed kind-level hits and flat-100-yen stake returns |
| `arvexq/prediction/prerace_archive.py` | Existing immutable before-off seal and outcome comparison, delegates payout details |
| `scripts/arvexq_capture_prerace_bet.js` | Load the same exact betting engine in server pre-off capture, hash model source |
| `build_static.py` | Fingerprint and copy separate web assets, fail if a dependency is missing |
| `arvexq/ui/static/app.js` | Original forecast + navigation coordinator, new decision/render functions now only thin bridges |

Do not copy the new three-way policy, rendering markup or payout calculations into app.js in future changes. Runtime order: three_way_engine, bet_view, app-v*.js. Existing legacy prediction/pace logic still resides in app.js and is not claimed to have been fully separated.
