#!/usr/bin/env node
'use strict';
// New elite status depends on historical verified ticket hits, never horse points.
const assert=require('node:assert/strict'),fs=require('node:fs');
const w={};
for(const file of ['ticket_lane_classifier','selection_cut','frozen_ticket_evidence'])
  new Function('window',fs.readFileSync('arvexq/ui/static/morning/'+file+'.js','utf8'))(w);
const lanes=w.ARVEXQMorningTicketLanes,cut=w.ARVEXQMorningSelection;
const chronological=(a,b)=>a.race.startTime.localeCompare(b.race.startTime);
const make=(id,t,prob,pts=1)=>({race:{id,raceNumber:1,startTime:t},
 selection:{selected:true,score:Math.round(prob*100),hitRate:prob,hitRateSamples:32,
 hitRateWilsonLower:.72,primaryType:'的中重視型',types:['的中重視型']}});
let rows=[make('late','15:10',.87),make('early','10:10',.82),make('under','13:10',.79),
 {race:{id:'bad',raceNumber:2,startTime:'09:10'},selection:{selected:false,score:99,hitRate:.96,
 hitRateSamples:32,hitRateWilsonLower:.72,primaryType:'的中重視型',types:['的中重視型']}}];
assert.deepEqual(cut.allStrictQualifiers(rows,{n:Number,chronological}).map(x=>x.race.id),['early','late']);
rows[0].selection.score=45;
assert.deepEqual(cut.allStrictQualifiers(rows,{n:Number,chronological}).map(x=>x.race.id),['early','late'],
 'ability model points are irrelevant to elite selection');
rows[0].selection.hitRateSamples=4;
assert.deepEqual(cut.allStrictQualifiers(rows,{n:Number,chronological}).map(x=>x.race.id),['early']);
rows[0].selection.hitRateSamples=32;
const horses=Array.from({length:8},(_,i)=>({horse:{horseNumber:i+1},predMark:i===0?'◎':'',
  threeFactorCoverage:3}));
const offer=lanes.classify({circuit:'地方'},{rows:horses},{score:30});
assert(offer.selected,'low ability score does not disqualify a ticket with prior hit evidence');
const goodPlan={decision:'購入候補',betInputGate:{ready:true},items:[{level:'本線',kind:'ワイド',combos:[[1,2]]}]};
assert.equal(lanes.requireMorningTickets(offer,goodPlan).selected,false,'no calibration -> no elite pick');
w.ARVEXQTicketHitCalibration={version:'arvexq-empirical-ticket-hit-v1',
 asOfDate:'2026-10-13',byCircuit:{'地方':{modelVersion:'arvexq-true-run-pure-sectional-v2',
 buckets:{'ワイド|1':{kind:'ワイド',points:1,sample:32,wins:28,
 hitRate:.875,wilsonLower95:.72,qualified:true}}}}};
assert.equal(lanes.requireMorningTickets(offer,goodPlan).selected,false,'old model calibration is prohibited');
w.ARVEXQTicketHitCalibration.byCircuit['地方'].modelVersion='arvexq-nar-track-condition-stage-v1';
const selected=lanes.requireMorningTickets(offer,goodPlan);
assert.equal(selected.selected,true);
assert.equal(selected.hitRate,.875);
assert.equal(selected.score,88);
assert.equal(selected.primaryType,'的中重視型');
assert.equal(lanes.requireMorningTickets(offer,{...goodPlan,
 items:[{level:'本線',kind:'馬連',combos:[[1,2]]}]}).selected,false,'no ticket-kind leakage');
assert.equal(lanes.requireMorningTickets(offer,{...goodPlan,decision:'見送り'}).selected,false);
assert.equal(lanes.requireMorningTickets(offer,{...goodPlan,betInputGate:{ready:false}}).selected,false);
assert.equal(lanes.requireMorningTickets(offer,{...goodPlan,
 items:[{level:'本線',kind:'ワイド',combos:[[1,1]]}]}).selected,false,'invalid combos');
w.ARVEXQTicketHitCalibration.byCircuit['地方'].buckets['ワイド|1'].sample=3;
assert.equal(lanes.requireMorningTickets(offer,goodPlan).selected,false);
// Previously archived tickets remain verifiable as historical receipts.
const oldRace={id:'old-original',date:'2026-10-11',startTime:'12:00'};
const oldMarks=Array.from({length:8},(_,i)=>({horse:{horseNumber:i+1},
 predMark:i===0?'◎':i===1?'○':'△',singleWinSuitable:i===0}));
const oldPlan={decision:'通常買い',betInputGate:{ready:true},
 items:[{level:'本線',kind:'ワイド',combos:[[1,2]]}]};
const oldSel={selected:true,primaryType:'的中重視型',types:['的中重視型'],ticketKinds:['ワイド']};
const evidence=w.ARVEXQMorningEvidence.capture(oldRace,{rows:oldMarks},oldPlan,oldSel);
assert(evidence,'old receipt preserved regardless of new empirical slate');
evidence.fixedAt='2026-10-11T06:30:00+09:00';
assert.equal(lanes.selectionDisplayStatus({...oldSel,ticketEvidence:evidence},oldRace),'actionable');
assert.equal(lanes.selectionDisplayStatus({...oldSel,ticketEvidence:{...evidence,
 fixedAt:'2026-10-11T13:00:00+09:00'}},oldRace),'ticket-original-missing');
console.log('MORNING_EMPIRICAL_HIT_AND_HISTORICAL_ORIGINALS_PASS');
