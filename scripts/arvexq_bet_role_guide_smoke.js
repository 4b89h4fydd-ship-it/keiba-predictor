'use strict';
// Exercise the actual isolated betting renderer without a browser dependency.
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
assert.doesNotMatch(html,/<i>【(?:単|軸)】<\/i>/);
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
const app=fs.readFileSync('arvexq/ui/static/app.js','utf8');
const postBet=app.slice(app.indexOf('function buildAiBetPlan(r,p){'),app.indexOf('function betItemHit('));
assert.match(postBet,/ARVEXQProductionTickets.build\(r,p\)/);
const postMark=app.slice(app.indexOf('function predict(r){'),app.indexOf('function nextRace(){'));
assert.doesNotMatch(postMark,/retrospectiveMarks/,'deleted legacy post-race recomputation');
assert.match(postMark,/ARVEXQProductionPrediction.build\(r\)/,'only disabled production interface is active');
require('./test_support/production_ui.cjs').assertNoForecast({horses:[{horseNumber:1,mark:'◎'}],preRaceBet:historic});
console.log('BET_ROLE_GUIDE_AND_RETIRED_BETS_CONTRACT_OK');
