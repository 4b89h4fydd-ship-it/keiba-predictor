// Synthetic consistency regressions, NOT historical hit-rate validation.
//
// 2026-11-28 shell migration (commit 827df37): the in-app pace model
// (historicalWindow / minetaPastProfile and its corner-position
// profiles) was removed with the rich UI. Pace is now modelled
// server-side in the clean-forecast scenario mixture; the entry-table
// shell computes no running style and invents none. The leakage-safety
// contract this smoke protected (future observations must not be model
// inputs, missing corner data must not create an invented running
// style, no unapproved future simulation) is pinned in its current
// form: none of that machinery exists in the shell, and the production
// forecast interface still returns no forecast for a pace-only fixture.
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const src=fs.readFileSync('arvexq/ui/static/app.js','utf8');
for(const retired of ['function historicalWindow(','function minetaRaceContext(',
  'minetaPastProfile','function scenarioPlan(','prevLeader','leadRate'])
  assert(!src.includes(retired),'retired in-app pace model must stay removed: '+retired);
assert(!src.includes("if(!p.firstPos){x.expected='不明'"),
  'no invented running style fallback exists in the shell');
require('./test_support/production_ui.cjs').assertNoForecast({horses:[{horseNumber:1,recentRaces:[{finish:1,cornerPositions:[1,1]}]}]});
console.log('OBSERVED_PACE_LEAKAGE_SAFE_NO_UNAPPROVED_SIMULATION_OK');
