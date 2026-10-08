// Six pace indicators regression. Synthetic observations only, not hit-rate proof.
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const src=fs.readFileSync('arvexq/ui/static/app.js','utf8');
const a=src.indexOf('function historicalWindow('),b=src.indexOf('function minetaRaceContext(',a);
assert.ok(a>=0&&b>a,'historical model section must be available');
const n=(v,d=0)=>v===null||v===undefined||v===''||!Number.isFinite(Number(v))?d:Number(v);
const clamp=(v,l,h)=>Math.max(l,Math.min(h,v));
const weights=len=>Array.from({length:len},(_,i)=>Math.pow(.82,i));
const weighted=(v,w,def=.5)=>{let num=0,den=0;v.forEach((val,i)=>{if(val!=null){num+=val*(w[i]??1);den+=w[i]??1;}});return den?num/den:def};
const model=new Function('n','clamp','recencyWeights','raceField','weightedRate','mean','sameCondition',
  src.slice(a,b)+'\nreturn {historicalWindow,styleRates,finishingEvidence,holdRate,lateGainScore,fadeRate,moveRate,breakReliability};')(
  n,clamp,weights,r=>Math.max(4,n(r&&r.fieldSize,12)),weighted,
  v=>v.reduce((q,x)=>q+x,0)/Math.max(v.length,1),(x,y)=>x===y);
const target={date:'2026-10-08',track:'大井',distance:1400,condition:'良'};
function run(day,first,last,finish,extra={}){
  return {date:day,track:'大井',distance:1400,raceNumber:4,fieldSize:12,
          cornerPositions:first===null?[]:[first,first,last,last],
          finish,...extra};
}
const history=[
 run('2026-09-30',1,1,2),
 run('2026-09-25',2,2,2),
 run('2026-09-20',5,4,1),
 run('2026-09-15',9,7,3),
 run('2026-09-10',1,1,10),
 run('2026-09-05',1,1,1), // Must never replace a weak recent result.
 run('2026-10-09',1,1,1), // Future leakage.
];
const h={recentRaces:history,allPastRuns:history.slice(0,3),
         precomputedMetrics:{style:{front:1,stalk:0,mid:0,close:0,samples:100}}};
const window=model.historicalWindow(h,target);
assert.equal(window.length,5,'exactly newest five starts before target');
assert.equal(window[0].date,'2026-09-30');
assert.equal(window[4].date,'2026-09-10');
const rates=model.styleRates(h,target);
assert.equal(rates.samples,5);
assert.equal(rates.availableRuns,5);
assert.ok(rates.front>.2&&rates.front<.7,'source-backed front share, not stale precompute 100%');
assert.ok(Math.abs(rates.front+rates.stalk+rates.mid+rates.close-1)<1e-10);
const finish=model.finishingEvidence(h,target);
assert.equal(finish.holdSamples,3);
assert.equal(finish.closingSamples,2);
assert.ok(finish.hold>0&&finish.hold<1,'front failure included, older victory excluded');
assert.equal(finish.closing,1,'last-corner trailing horse twice converted to top 3');
const completeWithMissing=history.slice(0,5).map((r,i)=>i===0?run('2026-09-30',null,null,0):r);
const thin={recentRaces:[...completeWithMissing,run('2026-09-05',1,1,1)]};
assert.equal(model.historicalWindow(thin,target).length,5);
assert.equal(model.styleRates(thin,target).samples,4,'missing recent first corner never backfilled with 6th run');
const noResult={recentRaces:[run('2026-09-30',1,null,null)]};
assert.equal(model.finishingEvidence(noResult,target).holdSamples,0);
assert.ok(model.holdRate(noResult,target)<=.5,'unknown finish is not a successful front hold');
const compact={date:'20261008',track:'大井',distance:1400};
assert.equal(model.historicalWindow(h,compact).length,5,'compact dates are accepted');
const empty={recentRaces:[]};
assert.equal(model.styleRates(empty,target).unknown,true);
assert.equal(model.finishingEvidence(empty,target).holdSamples,0);
const closing={recentRaces:[run('2026-09-30',8,7,2),run('2026-09-20',9,8,1),run('2026-09-10',7,6,3)]};
const front={recentRaces:[run('2026-09-30',1,1,1),run('2026-09-20',2,2,2),run('2026-09-10',1,1,2)]};
assert.ok(model.finishingEvidence(closing,target).closing>model.finishingEvidence(front,target).closing,
  'late converters must have independent evidence');
assert.ok(model.finishingEvidence(front,target).hold>model.finishingEvidence(closing,target).hold,
  'front retention must be evaluated separately');
assert.ok(src.includes('finishEvidence:finishingEvidence(h,r)'), 'buildRows must include observed finish evidence');
assert.ok(src.includes('x.finishEvidence.closingSamples/3'), 'closing score must use measured conversion');
assert.ok(src.includes('y.finishEvidence.holdSamples/3'), 'front stay score must use measured holding');
assert.ok(src.includes('y.finishEvidence.closingSamples/3'), 'come from behind must use measured conversion');
assert.ok(src.includes('的中確率ではありません'), 'UI must not equate internal score to empirical accuracy');
console.log('SIX_PACE_METRICS_OK newest5/dedupe/corners/finish-conversion/no-leakage/no-invented-rate');
