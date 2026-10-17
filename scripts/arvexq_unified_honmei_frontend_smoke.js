'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs');
const source=fs.readFileSync('arvexq/ui/static/app.js','utf8');
const start=source.indexOf('function assignObservedPredictionMarks('),end=source.indexOf('function buildObservedBetPlan(',start);
assert(start>=0&&end>start);
const assign=new Function('narScoreRows','n','observedCircuitLabel','observedModelVersion','assignIndependentSpecialMarks',
  source.slice(start,end)+';return assignObservedPredictionMarks;')(
  ()=>{},(v,d=0)=>Number(v)||d,()=> '地方',()=> 'test-observed',
  rows=>Object.fromEntries(rows.map((z,i)=>[z.horse.horseNumber,{mark:['◎','○','▲','△'][i]||''}])));
const rows=[.9,.65,.5,.4,.3].map((score,i)=>({horse:{horseNumber:i+1,integratedEvaluation:{}},
  narScore:score,narEvidence:{available:true,position:score,margin:score,sample:5},
  historicalRates:{top3Evidence:i===1?1:0},evaluation:{}}));
const race={};assign(rows,race);
assert.equal(rows.filter(z=>z.predMark==='◎').length,1);
assert.deepEqual(rows.filter(z=>z.preOffAxisCandidate).map(z=>z.horse.horseNumber),[1]);
assert.equal(race.honmeiDecisionFrontend.axisHorseNumber,race.honmeiDecisionFrontend.horseNumber);
assert.equal(race.honmeiDecisionFrontend.role,'win-axis');
assert.equal(rows[0].horse.integratedEvaluation.honmeiRole,'win-axis');
assert(!rows.some(z=>z.honmeiRole==='axis'));
const hash=JSON.stringify(rows[0].horse.integratedEvaluation);
assert(source.includes('window.ARVEXQ_HONMEI_POLICY="unified-win-axis-v1"'));
console.log('UNIFIED_FRONTEND_HONMEI_SELECTION_PASS');
