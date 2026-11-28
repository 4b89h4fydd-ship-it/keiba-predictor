'use strict';
// Exercise the actual isolated betting renderer without a browser dependency.
//
// 2026-11-28 shell migration (commit 827df37): the app shell was rebuilt
// as an entry-table-only viewer (user-confirmed final form). app.js no
// longer builds bet plans or predictions at all: it renders the marks
// and probabilities already fixed in the static race pack. The tail of
// this smoke therefore pins the current shell contract instead of
// slicing the retired buildAiBetPlan/predict functions out of app.js:
// - the retired in-app plan/prediction wiring stays absent, and
// - the disabled production interface (forecast modules) is still the
// only forecast surface, verified through production_ui.cjs.
// The bet_view.js renderer contract above is unchanged.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('arvexq/ui/static/betting/bet_view.js','utf8');
const context = {window:{}};
vm.runInNewContext(source,context,{filename:'bet_view.js'});
const renderer=context.window.ARVEXQBetView.render;
const esc=x=>String(x??'').replace(/&/g,'&amp;').replace(/</g,'&lt;');
const plan={decision:'見送り',betQuality:55,items:[],referenceBudget:{points:0},reason:'見送り'};
const deps={
buildAiBetPlan:()=>plan,esc,n:x=>Number(x||0),isFinal:()=>false,
raceMarkClock:()=>({started:false}),aiBetExplanationHtml:()=>'',betComboText:()=>''
};
const html=renderer({},{},deps);
assert.match(html,/<i>◎<\/i>勝ち切る能力と3着内の安定性/);
assert.doesNotMatch(html,/<i><\/i>/);
assert.match(html,/<i>☆<\/i>/);
assert.doesNotMatch(html,/☆\+/);
assert.match(html,/目標の的中率80%以上.*保証するものではありません/);
// Display-only unification must preserve every selected ticket and its points.
const allKinds={...plan,decision:'推奨',items:[
{level:'本線',kind:'ワイド',points:1,combo:'1 - 2',combos:[[1,2]]},
{level:'3連単チャレンジ',kind:'3連単',points:1,combo:'1 - 2 - 3',combos:[[1,2,3]]},
{level:'保険',kind:'馬連',points:1,combo:'1 - 3',combos:[[1,3]]}
]};
const unified=renderer({}, {}, {...deps,buildAiBetPlan:()=>allKinds});
assert.equal((unified.match(/class="arv-three-section"/g)||[]).length,1);
assert.match(unified,/<h3>おすすめ買い目<\/h3>/);
for(const combo of ['1 - 2','1 - 2 - 3','1 - 3'])assert.ok(unified.includes(combo),combo);
assert.doesNotMatch(unified,/<h3>(?:本線|3連単チャレンジ|保険)/);
assert.equal(allKinds.items.length,3,'source plan must be unchanged');
const historic={...plan,fixedAt:'2026-10-08T10:20:00+09:00',
engineVersion:'arvexq-bets-old-v317',
items:[{level:'本線',kind:'馬連',points:1,combo:'2 - 6',combos:[[2,6]]}]};
const old=renderer({},{},{...deps,buildAiBetPlan:()=>historic});
assert.match(old,/発走前固定/);
assert.match(old,/2 - 6/);
const revised=renderer({},{},{...deps,buildAiBetPlan:()=>({...plan,postRaceRevision:true})});
assert.match(revised,/事後分析（発走後再計算）/);
assert.match(revised,/的中率の検証には使用しません/);
// Current shell contract (replaces the retired app.js function slices):
// the entry-table shell never builds plans or predictions in the client,
// so no post-race recomputation can exist there either.
const app=fs.readFileSync('arvexq/ui/static/app.js','utf8');
assert(!app.includes('function buildAiBetPlan('),'retired in-app bet plan builder must stay removed');
assert(!app.includes('function betItemHit('),'retired in-app bet scoring must stay removed');
assert(!app.includes('function predict('),'retired in-app prediction must stay removed');
assert(!app.includes('retrospectiveMarks'),'deleted legacy post-race recomputation');
assert(!app.includes('ARVEXQProductionTickets.build'),'shell must not wire the production ticket interface');
assert(!app.includes('ARVEXQProductionPrediction.build'),'shell must not wire the production prediction interface');
// The shell displays only what the static pack already fixed.
assert(app.includes('function marksByNumber('),'shell reads pack marks by horse number');
assert(app.includes('unifiedForecast'),'shell renders the pack unifiedForecast only');
require('./test_support/production_ui.cjs').assertNoForecast({horses:[{horseNumber:1,mark:'◎'}],preRaceBet:historic});
console.log('BET_ROLE_GUIDE_AND_RETIRED_BETS_CONTRACT_OK');
