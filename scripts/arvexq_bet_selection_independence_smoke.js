#!/usr/bin/env node
'use strict';
// A published "厳選" label is not a prerequisite for a separately evidenced
// regular/special ticket. No original morning race is reclassified.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const app=fs.readFileSync('arvexq/ui/static/app.js','utf8');
const src=fs.readFileSync('arvexq/ui/static/betting/bet_readiness.js','utf8');
const win={};new Function('window',src)(win);
const start=app.indexOf('function rebuildBetStrategyV242(');
const end=app.indexOf('function immutableStoredAiBetView(',start);
assert.ok(start>0&&end>start,'ticket selection wrapper exists');
const n=(x,d=0)=>x!==null&&x!==undefined&&x!==''&&Number.isFinite(Number(x))?Number(x):d;
const clamp=(x,a=0,b=1)=>Math.max(a,Math.min(b,x));
const ready={card:.94,history:.72,analysis:.71,prediction:.78,
 actualOdds:0,bodyWeight:0,environment:.5};
const deps={
 window:{ARVEXQBetReadiness:win.ARVEXQBetReadiness},
 n,clamp,
 dataReadinessProfile:()=>ready,
 arvexqRaceType:()=>({code:'standard',label:'標準',orderReadable:true}),
 betComboText:(kind,cs)=>cs.map(c=>c.join(kind==='馬単'||kind==='3連単'?' → ':' - ')).join(' / ')
};
const rebuild=new Function(...Object.keys(deps),app.slice(start,end)+';return rebuildBetStrategyV242;')(...Object.values(deps));
const rows=Array.from({length:8},(_,i)=>({
 horse:{horseNumber:i+1,name:'馬'+i},predMark:i===0?'◎':'△',
 axisConfidence:i===0?.85:0,winnerDecisionStable:i===0
}));
const race={id:'jra-future-test',date:'2026-10-13',circuit:'中央',
 track:'東京',raceNumber:11,horses:rows.map(x=>x.horse)};
const pred={rows,coverage:.74};
const item=(kind,combos)=>({kind,combos,points:combos.length,level:'通常'});
const draft=()=>({
 selectionAudit:{selected:false,score:46,evidence:.42,reason:'厳選外'},
 betQuality:78,featuredRace:true,
 items:[item('ワイド',[[1,2],[1,3]]),item('馬連',[[1,2],[2,3]]),
        item('3連複',[[1,2,3]]),item('馬単',[[1,2]]),
        item('3連単',[[1,2,3],[1,3,2],[1,2,4],[1,4,2],[1,3,4],[1,4,3]])],
 roles:{p1:[{no:1,p:.48},{no:2,p:.22},{no:3,p:.13}]},
 audit:{field:8,p1Top:.48,p1Margin:.26,top2mass:.70,top3mass:.83,entropy:.65,
 orderConfidence:.77,quinTop:.22,quinRatio:1.48,trioTop:.14,trioRatio:1.45,
 exactaTop:.16,exactaRatio:1.35,wideTop:.30,wideRatio:1.48,triTop6:.24,triRatio:1.6}
});
const previous=draft(),independent=rebuild(previous,race,pred);
assert.equal(previous.selectionAudit.selected,false,'published selection never changes');
assert.equal(independent.selectionAudit.selected,false,'independent ticket must not forge selection');
assert.equal(independent.referenceOnly,true,'separately qualified regular/special ticket');
assert.ok(independent.items.length>0,'data-supported regular/special must reach ticket choice');
assert.ok(['通常買い','強く買う'].includes(independent.decision),'no generic strict-elite veto');
const elite=draft();elite.selectionAudit.selected=true;
const selected=rebuild(elite,race,pred);
assert.ok(selected.items.length>0,'elite remains allowed');
const weak=draft();weak.selectionAudit.score=5;weak.selectionAudit.evidence=.05;
const blocked=rebuild(weak,race,pred);
assert.equal(blocked.decision,'見送り','no missing-quality bypass');
assert.deepEqual(blocked.items,[],'weak reference does not buy');
const sparse=rebuild(draft(),{...race,_entryOnly:true},pred);
assert.equal(sparse.decision,'見送り','bare roster is not sufficient analysis');
assert.equal(sparse.referenceOnly,undefined);
console.log('BET_SELECTION_INDEPENDENCE_OK regular='+independent.items.map(x=>x.kind).join('・')+
 ' elite='+selected.items.length+' weak=skipped static=skipped');
