// Legacy pre-off ticket source must be labelled separately from current marks.
const assert=require('node:assert/strict'),fs=require('node:fs');
const ui=fs.readFileSync('arvexq/ui/static/app.js','utf8');
assert(ui.includes('function racecardMarkLegend(r)'));
assert(ui.includes('arv-race-mark-source-note'));
assert(ui.includes('frozenAiBetForRace(r)'));
const source=fs.readFileSync('arvexq/ui/static/betting/bet_view.js','utf8');
const root={};new Function('window',source)(root);
const plan={raceId:'nar-2026-10-13-盛岡-06',raceDate:'2026-10-13',
  engineVersion:'arvexq-old-selection-v345',fixedAt:'2026-10-12T21:54:31.159Z',
  decision:'通常買い',items:[{level:'本線',kind:'馬連',points:2,
    combos:[[8,11],[6,11]]}]};
const deps={buildAiBetPlan:()=>plan,esc:String,n:Number,isFinal:()=>false,
 raceMarkClock:()=>({started:false}),aiBetExplanationHtml:()=>'',betComboText:(kind,combinations)=>combinations.map(x=>x.join(' - ')).join(' / ')};
const html=root.ARVEXQBetView.render({id:plan.raceId}, {rows:[]}, deps);
assert.match(html,/発走前保存済み買い目（旧方式）/);
assert.match(html,/2026\/10\/13.{0,3}06:54 JST/);
assert.match(html,/印と買い目の判定時点が異なります/);
assert.match(html,/無印の馬が保存買い目に入る場合があります/);
assert.match(html,/8 - 11 \/ 6 - 11/);
assert.deepEqual(plan.items[0].combos,[[8,11],[6,11]],'immutable combinations');
assert.equal(plan.fixedAt,'2026-10-12T21:54:31.159Z','immutable timestamp');
console.log('LEGACY_BET_CURRENT_MARK_DIFFERENCE_EXPLAINED_OK');
