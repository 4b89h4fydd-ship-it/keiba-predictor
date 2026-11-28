#!/usr/bin/env node
'use strict';
// Visible honmei roles under the 2026-11-28 shell migration
// (commit 827df37, user-confirmed entry-table-only app).
//
// The retired shell labelled marks through markRoleLabel() and rendered
// them via racecardEntryRow()/aiMarksPanel(). The contract was: role
// labels come only from the mark itself, frozen roles stay labelled as
// saved, and no independent fixed-weight axis score may exist. The
// current shell has no role labels and no mark panels: the mark column
// shows the pack's unifiedForecast.marks value verbatim. This smoke
// pins that contract and keeps the production-interface check.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const src=fs.readFileSync('arvexq/ui/static/app.js','utf8');
for(const retired of ['function markRoleLabel(','function racecardEntryRow(',
  'function aiMarksPanel(','function betPanel(','rc-honmei-role','rc-mark-box',
  'data-user-mark','honmeiRole','axisScore:.45*stable'])
  assert(!src.includes(retired),'retired honmei display machinery must stay removed: '+retired);
assert(src.includes('function marksByNumber('),'mark column source is the pack marks map');
assert(src.includes("marks[row.number] || ''"),'mark cell renders the pack value verbatim');
require('./test_support/production_ui.cjs').assertNoForecast({horses:[{horseNumber:1,mark:'◎',honmeiRole:'win-axis'}]});
console.log('VISIBLE_HONMEI_ROLES_OK');
