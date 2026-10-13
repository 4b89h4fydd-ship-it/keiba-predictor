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
assert.match(html,/<i>【単】<\/i>◎【単】/);
assert.match(html,/<i>【軸】<\/i>◎【軸】/);
assert.match(html,/<i>☆<\/i>/);
assert.doesNotMatch(html,/☆\+/);
assert.doesNotMatch(html,/的中率80%|的中率100%/);
const historic={...plan,fixedAt:'2026-10-08T10:20:00+09:00',
 engineVersion:'arvexq-bets-old-v317',
 items:[{level:'本線',kind:'馬連',points:1,combo:'2 - 6',combos:[[2,6]]}]};
const old=renderer({},{},{...deps,buildAiBetPlan:()=>historic});
assert.match(old,/現行方式の発走前買い目は未保存です/);
assert.doesNotMatch(old,/2 - 6/);
console.log('BET_ROLE_GUIDE_AND_RETIRED_BETS_CONTRACT_OK');
