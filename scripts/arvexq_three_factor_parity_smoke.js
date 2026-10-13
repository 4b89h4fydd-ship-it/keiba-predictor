#!/usr/bin/env node
'use strict';
// Executable contract for the one active 45/35/20 scoring method.
const assert=require('node:assert/strict'),fs=require('node:fs');
const src=fs.readFileSync('arvexq/ui/static/app.js','utf8');
const start=src.indexOf('function arvexqFactorValues(');
const end=src.indexOf('function arvexqRacePolicy(',start);
assert(start>=0&&end>start,'new factors must be part of the real predictor');
const model=new Function(src.slice(start,end)+'; return arvexqFactorValues;')();
const hist=[1,2,1,2,1].map((finish,i)=>({
  date:'2026-10-'+String(11-i*2).padStart(2,'0'),
  fieldSize:12,finish,last3fRank:finish,track:'園田',distance:1400
}));
const horse={horseNumber:1,recentRaces:hist,allPastRuns:hist,
  integratedEvaluation:{v218Audit:{trueRun:0,pure:0,sectional:0}}};
const x=model({horse},{date:'2026-10-13'});
const q=hist.map(h=>(12-h.finish)/11);
const tr=q.reduce((sum,v,i)=>sum+v*(5-i),0)/15;
const sorted=q.slice().sort((a,b)=>a-b);
const pure=(sorted[4]+sorted[2])/2, sec=q.reduce((a,b)=>a+b,0)/5;
const expected=.45*tr+.35*pure+.20*sec;
assert.equal(x.coverage,3);
assert(Math.abs(x.score-expected)<1e-12,'three direct pre-off factors and weights');
assert(!src.slice(start,end).includes('v218Audit'),'old v218 model score cannot rank horses');
horse.recentRaces.push({date:'2026-10-14',fieldSize:12,finish:1,last3fRank:1});
assert(Math.abs(model({horse},{date:'2026-10-13'}).score-expected)<1e-12,'future excluded');
const absent=model({horse:{recentRaces:[]}},{date:'2026-10-13'});
assert.equal(absent.coverage,0);
assert.equal(absent.score,.5,'missing cannot create a fabricated 80+ elite rating');
console.log('THREE_FACTOR_PARITY_OK TRUE_RUN_45 PURE_35 SECTIONAL_20');
