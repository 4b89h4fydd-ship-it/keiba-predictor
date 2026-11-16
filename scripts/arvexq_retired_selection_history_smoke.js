const assert=require('node:assert/strict'),fs=require('node:fs');
const src=fs.readFileSync('arvexq/ui/static/app.js','utf8');
assert(!src.includes('function legacyMorningSelectionCandidates('));
assert(!src.includes('arv-pick-history'));
assert(!src.includes('朝選定（買い目原本未確認）'));
assert(src.includes('function selectedRaceCandidates('));
assert(src.includes("String(m.selectionModelVersion||'')==='arvexq-empirical-ticket-hit-v1'"),'empirical ticket calibration gate retained');
assert(!src.includes("n(m.selectedScore,0)>=80"),'ability-based 80 point selection gate must be retired');
// The selection (厳選) page itself was removed with the selection UI
// (PR #544, user directive 2026-11-16); it must not come back.
assert(!src.includes('function selectedCircuitPage('));
assert(src.includes("function homeCircuitChooser("));
console.log('RETIRED_UNVERIFIED_SELECTION_HISTORY_HIDDEN_OK');
