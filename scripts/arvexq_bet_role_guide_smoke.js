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
assert.match(postBet,/if\(stored\)return immutableStoredAiBetView\(r,stored\);/);
const postMark=app.slice(app.indexOf('function predict(r){'),app.indexOf('function nextRace(){'));
assert.doesNotMatch(postMark,/retrospectiveMarks/,'deleted legacy post-race recomputation');
assert.match(postMark,/learnedD1Prediction\(r\)/,'D1 marks are authoritative');
console.log('BET_ROLE_GUIDE_AND_RETIRED_BETS_CONTRACT_OK');
