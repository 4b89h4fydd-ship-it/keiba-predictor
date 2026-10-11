#!/usr/bin/env node
'use strict';
// Evidence preparation never forges the fixed elite decision or chooses tickets.
const assert=require('node:assert/strict'),fs=require('node:fs');
const app=fs.readFileSync('arvexq/ui/static/app.js','utf8');
const win={};
new Function('window',fs.readFileSync('arvexq/ui/static/betting/bet_readiness.js','utf8'))(win);
for(const fn of ['rebuildBetStrategyV242','buildV213AiBetPlan','forceMandatoryTrifecta','alignBetPlanToOutcome'])
 assert.ok(!app.includes('function '+fn+'('),'obsolete selector remains: '+fn);
const begin=app.indexOf('function prepareBetEvidence('),end=app.indexOf('// Dedicated betting policy:',begin);
assert.ok(begin>0&&end>begin,'readiness preparation exists');
const n=(x,d=0)=>x!==null&&x!==undefined&&x!==''&&Number.isFinite(Number(x))?Number(x):d;
const clamp=(x,a=0,b=1)=>Math.max(a,Math.min(b,x));
const rd={card:.94,history:.72,analysis:.71,prediction:.78,actualOdds:0,bodyWeight:0,environment:.5};
const prepare=new Function('window','paceEvidenceProfile','dataReadinessProfile','arvexqRaceType','n','clamp','morningPickOf',
 app.slice(begin,end)+';return prepareBetEvidence;')(
 win,()=>({ready:true,coverage:.8,topMissing:[],leaderMissing:[]}),()=>rd,
 ()=>({code:'standard',label:'標準'}),n,clamp,()=>null);
const draft=()=>({selectionAudit:{selected:false,score:47,evidence:.56,reason:'厳選外'},
 items:[{kind:'馬連',combos:[[1,2]],points:1}],decision:'暫定',audit:{orderConfidence:.7},
 betQuality:82,reason:'model audit'});
const race={id:'preoff',circuit:'中央',date:'2026-10-13',careerReadiness:{ready:true}};
const p={rows:Array.from({length:8},(_,i)=>({horse:{horseNumber:i+1}})),coverage:.72};
const regular=prepare(draft(),race,p);
assert.equal(regular.selectionAudit.selected,false);
assert.equal(regular.referenceOnly,true,'quality-qualified regular race');
assert.equal(regular.betInputGate.ready,true);
assert.equal(regular.decision,'暫定','readiness must not choose');
assert.deepEqual(regular.items,[{kind:'馬連',combos:[[1,2]],points:1}]);
const weak=draft();weak.selectionAudit.score=8;weak.selectionAudit.evidence=.07;
assert.equal(prepare(weak,race,p).referenceOnly,undefined,'weak not promoted');
const elite=draft();elite.selectionAudit.selected=true;
assert.equal(prepare(elite,race,p).selectionAudit.selected,true);
const sparse=prepare(draft(),race,{...p,rows:p.rows.slice(0,3)});
assert.equal(sparse.betInputGate.ready,false);
assert.equal(sparse.decision,'暫定','data gap not discretionary skip');
assert.ok(!app.includes('.qualifyPlaceBet('),'old morning selected mutation removed');
console.log('BET_SELECTION_INDEPENDENCE_OK regular=reference elite=untouched legacy-selector=deleted');
