'use strict';
// Visible axis mark integrity under the 2026-11-28 shell migration
// (commit 827df37, user-confirmed entry-table-only app).
//
// The retired shell rendered marks through markRoleLabel /
// visiblePredictionMark / racecardEntryRow. The regression protected
// here was: display code must never fabricate, promote or mutate a
// mark (a live axis candidate must not become a displayed ◎, a retired
// mark must not be restored, a scratched runner must not gain a mark).
// The current shell has no mark roles at all: the mark column shows
// exactly the pack's unifiedForecast.marks value for that horse number
// (marksByNumber), and nothing in the shell assigns or rewrites a mark.
// This smoke pins that contract, and re-checks through the production
// forecast interface that an axis candidate still yields no mark.
const fs=require('node:fs'),assert=require('node:assert/strict');
const src=fs.readFileSync('arvexq/ui/static/app.js','utf8');
for(const retired of ['function markRoleLabel(','function visiblePredictionMark(',
  'function racecardEntryRow(','preOffAxisCandidate','honmeiRole','predMark',
  'data-ai-mark','rc-mark-box','racecardMarkCellHtml(','ARVEXQMarkFrame'])
  assert(!src.includes(retired),'retired mark display machinery must stay removed: '+retired);
assert(src.includes('function marksByNumber('),'mark column source is the pack marks map');
assert(src.includes('uf.marks'),'shell reads unifiedForecast.marks only');
assert(src.includes("marks[row.number] || ''"),'mark cell renders the pack value verbatim, blank when absent');
require('./test_support/production_ui.cjs').assertNoForecast({
  horses:[{horseNumber:6,name:'ホウオウバトラー',frameNumber:5,sex:'牡',age:3,jockey:'小笠鈴'}]});
console.log('UNIFIED_VISIBLE_HONMEI_OK no_independent_axis_promotion existing_marks_untouched frozen_immutable');
