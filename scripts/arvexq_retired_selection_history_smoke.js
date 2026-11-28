const assert=require('node:assert/strict'),fs=require('node:fs');
const src=fs.readFileSync('arvexq/ui/static/app.js','utf8');
assert(!src.includes('function legacyMorningSelectionCandidates('));
assert(!src.includes('arv-pick-history'));
assert(!src.includes('朝選定（買い目原本未確認）'));
// 2026-11-28 shell migration (commit 827df37): the selection UI was
// already removed from the old shell (PR #544) and the remaining home /
// selection helpers (selectedRaceCandidates, homeCircuitChooser, the
// in-app empirical-gate string) were removed with the rich UI. The
// entry-table shell has no selection surface at all; selection lives
// server-side (morning modules + post generation). Pin that absence,
// and pin the shell's actual home (venue list) as the positive anchor.
assert(!src.includes('function selectedRaceCandidates('),'selection candidates removed with the selection UI');
assert(!src.includes("String(m.selectionModelVersion||'')==='arvexq-empirical-ticket-hit-v1'"),
  'in-app empirical gate removed; the gate itself is covered in the morning modules');
assert(!src.includes("n(m.selectedScore,0)>=80"),'ability-based 80 point selection gate must be retired');
assert(!src.includes('function selectedCircuitPage('));
assert(!src.includes('function homeCircuitChooser('),'retired circuit chooser removed with the rich UI');
assert(src.includes('function renderVenues('),'current home is the venue list');
console.log('RETIRED_UNVERIFIED_SELECTION_HISTORY_HIDDEN_OK');
