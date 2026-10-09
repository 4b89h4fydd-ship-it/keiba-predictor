#!/usr/bin/env node
'use strict';
const fs=require('node:fs'),assert=require('node:assert/strict');
const host={};
new Function('window',fs.readFileSync('arvexq/ui/static/betting/podium_axis_guard.js','utf8'))(host);
const g=host.ARVEXQPodiumAxisGuard;
assert.equal(g.VERSION,'arvexq-axis-reliability-v2-past-context');
function horse(outcomes){
 return {horseNumber:4,recentRaces:outcomes.map((finish,i)=>({
  date:'2026-09-'+String(25-i).padStart(2,'0'),track:'大井',
  surface:'ダート',distance:1200,condition:'良',fieldSize:10,
  finish,cornerPositions:[2,2,3,3],last3f:36.1
 }))};
}
const race={date:'2026-10-09',track:'大井',surface:'ダート',distance:1200,condition:'良'},
      past=g.analyzePast(horse([1,2,3,2,5]),race),
      runner={horse:{horseNumber:5},podiumAxisScore:.62},
      candidate={horse:{horseNumber:4},podiumPastFive:past,
       podiumAxisScore:.70,axisRank:1,podiumRecallRank:2,winnerDecisionRank:2,
       edgeEvidence:.55,coverage:.65};
assert.equal(past.datedRuns,5);
assert.equal(past.top3,4);
assert.equal(past.comparableTop3,4);
assert(g.inspect(candidate,runner).eligible,'comparable consistent horse supported');
function reject(patch,reason){
 const r=g.inspect({...candidate,...patch},runner);
 assert(!r.eligible,reason);
 assert(r.failures.includes(reason),JSON.stringify(r));
}
const short=g.analyzePast(horse([1,5]),race);
reject({podiumPastFive:short},'historyVerified');
reject({podiumPastFive:g.analyzePast(horse([8,9,1,2,3]),race)},'recentFormNotDeteriorating');
const fadeHorse=horse([9,8,2,2,2]);
reject({podiumPastFive:g.analyzePast(fadeHorse,race)},'noRepeatedFrontFade');
const mismatch=horse([1,2,3,2,2]);
mismatch.recentRaces.slice(0,3).forEach(x=>{x.distance=1600;});
const matched=g.analyzePast(mismatch,race);
assert.equal(matched.comparableRuns,2);
assert.equal(matched.comparableTop3,2);
const noPodium=horse([1,2,3,7,7]);
noPodium.recentRaces.forEach((x,i)=>{if(i<3)x.distance=1600});
reject({podiumPastFive:g.analyzePast(noPodium,race)},'matchingConditionEvidence');
reject({winnerDecisionRank:4},'winningChance');
reject({podiumAxisScore:.64},'clearSeparation');
reject({edgeEvidence:.2},'observedEvidence');
const future=horse([1,1,1,1,1]);future.recentRaces.forEach(x=>{x.date='2026-10-10'});
assert.equal(g.analyzePast(future,race).datedRuns,0,'future performances excluded');
assert(!g.inspect(null,null).eligible,'no forced axis');
console.log('PODIUM_AXIS_GUARD_OK five_dated_runs future_excluded risk_checks winner_head');
