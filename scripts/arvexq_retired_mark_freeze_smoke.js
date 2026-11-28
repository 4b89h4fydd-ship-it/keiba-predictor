const assert=require('node:assert/strict'),fs=require('node:fs');
const s=fs.readFileSync('arvexq/ui/static/app.js','utf8');
assert(!s.includes('loadFrozenMarks'),'retired device-only mark loader must be removed');
assert(!s.includes('saveFrozenMarks'),'retired device-only mark saver must be removed');
assert(!s.includes('local-prepost'),'retired local override must be removed');
assert(!s.includes('端末の発走前印・固定済み'),'retired device mark legend must be removed');
assert(!s.includes("record={version:'v345'"),'retired local mark seal must not be generated');
assert(!s.includes('localStorage.setItem(markFreezeKey(r)'), 'retired local mark seal must not be written');
assert(!s.includes('function serverFrozenPrediction('),'retired frozen-prediction publishing is prohibited');
assert(!s.includes('function assignPredictionMarks('),'retired mark generation is prohibited');
// 2026-11-28 shell migration (commit 827df37): the audit-receipt reader
// (authorizedPreOffMarks) and the live-mark interface call that lived in
// app.js were removed with the rich UI. The current contract is
// stronger and is pinned instead: the shell generates nothing and
// displays only the marks already fixed in the static pack, while the
// production marks interface itself stays disabled for unvalidated rows.
assert(!s.includes('function authorizedPreOffMarks('),'receipt reader removed with the rich UI');
assert(!s.includes('ARVEXQProductionMarks.visible'),'shell must not wire the marks interface');
assert(!s.includes('localStorage'),'shell keeps no device mark storage at all');
assert(s.includes('function marksByNumber('),'live marks must come from the pack unifiedForecast');
assert(s.includes('uf.marks'),'shell reads pack marks only');
const marksModule={};new Function('window',fs.readFileSync('arvexq/ui/static/forecast/marks.js','utf8'))(marksModule);
assert.equal(marksModule.ARVEXQProductionMarks.visible({predMark:'◎'}),'',
  'unvalidated rows expose no live mark through the production interface');
assert.equal(marksModule.ARVEXQProductionMarks.visible({predMark:'◎',serverPreoffMark:true}),'◎',
  'server-fixed pre-off originals remain displayable');
console.log('RETIRED_LOCAL_MARK_FREEZE_EXCLUDED_OK');
