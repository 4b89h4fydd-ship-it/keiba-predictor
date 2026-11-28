'use strict';
// Scratch (取消) integrity under the 2026-11-28 shell migration
// (commit 827df37, user-confirmed entry-table-only app).
//
// The retired shell merged live odds payloads into the displayed race
// (mergeOddsPayload / mergeHorseReflection / edgeOddsRow). Its contract
// was: once a horse is officially scratched, a later stale market reply
// can never re-enable it, its odds stay null, and stale predictions are
// invalidated. The current shell merges nothing — it renders the static
// pack exactly as built, and scratch state is fixed server-side when
// the pack is built (entry reconciliation against the official result).
// The client-side re-enable vector is therefore gone, and this smoke
// pins its absence: no odds merge, no scratch reflection, no odds
// rendering exists in the shell (the entry table shows no odds column
// at all, per the confirmed app form).
const assert = require('node:assert/strict');
const fs = require('node:fs');
const source = fs.readFileSync('arvexq/ui/static/app.js', 'utf8');
for(const retired of ['function isScratchHorse(','function mergeOddsPayload(',
  'function mergeHorseReflection(','function edgeOddsRow(','function reflectUseful(',
  'scratch-odds','取消'])
  assert(!source.includes(retired),'retired live odds/scratch reflection must stay removed: '+retired);
assert(source.includes('function raceRows('),'race rows come from the pack only');
assert(source.includes('function staticRaceUrl('),'race display is pack-driven only');
console.log('ARVEXQ_SCRATCH_LIVE_REFLECTION_OK');
