#!/usr/bin/env node
'use strict';
// Synthetic checks only. Relative model weights are not calibrated hit rates.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const load=(filename,target)=>{
 new Function('window',fs.readFileSync(filename,'utf8'))(target);
};
const w={};
load('arvexq/ui/static/betting/bet_readiness.js',w);
const mod=w.ARVEXQBetReadiness;
const horses=Array.from({length:8},(_,i)=>({
  horse:{horseNumber:i+1},predMark:i===0?'◎':'△',
  winnerDecisionProbability:[.32,.26,.17,.10,.06,.04,.03,.02][i]
}));
const race={id:'future',date:'2026-10-12',startTime:'12:00',circuit:'地方',
 careerReadiness:{ready:false,blockedHorses:[{horseNumber:8}]}};
const prediction={rows:horses,coverage:.48};
const rd={card:.94,history:.48,analysis:.54,prediction:.60,
 actualOdds:0,bodyWeight:0,environment:.5};
const observed={ready:true,coverage:.75,topMissing:[],leaderMissing:[]};
const gate=mod.evaluate(race,prediction,observed,rd);
assert.equal(gate.ready,true,'partial full-career acquisition must not veto all evidenced pair tickets');
assert.equal(gate.trifectaReady,false,'limited recent history must not trigger triple-order bets');
assert.equal(gate.oddsVerified,false,'missing live odds must not be invented');
assert(gate.warnings.some(x=>x.includes('全キャリア')),'incomplete career is explicitly disclosed');
const strict=mod.evaluate(race,prediction,observed,{...rd,history:.82,prediction:.72});
assert.equal(strict.trifectaReady,true,'complete recent/pace evidence allows independent trifecta review');
assert.equal(mod.evaluate(race,prediction,{...observed,coverage:0,topMissing:[1]},rd).ready,false,
 'missing winner pace evidence still blocks tickets');
assert.equal(mod.evaluate(race,{rows:horses.slice(0,3)},observed,rd).ready,false,
 'missing field remains blocked');
const reference=mod.promoteReference(
 {selectionAudit:{selected:false,score:43,evidence:.34,reason:'strict winner gate did not pass'}},
 race,prediction,rd);
assert.equal(reference.selectionAudit.selected,true,
 'usable ordinary/special race may receive a clearly labeled reference ticket');
assert.equal(reference.referenceOnly,true);
const unready=mod.promoteReference(
 {selectionAudit:{selected:false,score:43,evidence:.34}},race,prediction,{...rd,history:0});
assert.equal(unready.selectionAudit.selected,false,'reference tickets still require recent model evidence');
const opted=mod.promoteReference(
 {selectionAudit:{selected:false,score:4,evidence:.07}},race,prediction,rd);
assert.equal(opted.selectionAudit.selected,false,'quality controls are not completely removed');
const allReady=mod.evaluate({...race,careerReadiness:{ready:true}},prediction,observed,rd);
assert(!allReady.warnings.some(x=>x.includes('全キャリア')));
console.log('BET_USABILITY_SMOKE_OK partial-career=disclosed special-reference=enabled trifecta=independently-gated');