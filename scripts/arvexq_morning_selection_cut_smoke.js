'use strict';
// Synthetic regressions only. Morning picks are not calibrated hit rates.
const assert=require('node:assert/strict'),fs=require('node:fs');
const laneSource=fs.readFileSync('arvexq/ui/static/morning/ticket_lane_classifier.js','utf8');
const source=fs.readFileSync('arvexq/ui/static/morning/selection_cut.js','utf8');
const w={};new Function('window',laneSource)(w);new Function('window',source)(w);
const n=(v)=>Number(v)||0,chronological=(a,b)=>a.race.startTime.localeCompare(b.race.startTime);
const rows=[
 {race:{id:'JRA-01',raceNumber:5,startTime:'13:10'},selection:{selected:true,score:70}},
 {race:{id:'NAR-02',raceNumber:10,startTime:'18:10'},selection:{selected:true,score:66}},
 {race:{id:'NAR-01',raceNumber:2,startTime:'10:00'},selection:{selected:true,score:72}},
 {race:{id:'NOT-QUALIFIED',raceNumber:1,startTime:'09:50'},selection:{selected:false,score:98}},
];
const x=w.ARVEXQMorningSelection.allStrictQualifiers(rows,{n,chronological});
assert.deepEqual(x.map(z=>z.race.id),['NAR-01','JRA-01','NAR-02'],'all eligible races kept, no max-one cap');
assert.equal(w.ARVEXQMorningSelection.version,'strict-unlimited-morning-v1');
console.log('MORNING_SELECTION_UNLIMITED_OK '+x.length);

function laneTest(overrides={}){
 const rows=Array.from({length:8},(_,i)=>({
   horse:{horseNumber:i+1},predMark:i===0?'◎':i===4?'☆+':i===1?'○':'△',
   ticketP2Probability:[.31,.26,.18,.09,.08,.04,.025,.015][i],
   ticketP3Probability:[.25,.24,.18,.11,.10,.06,.04,.02][i]}));
 const audit={selected:false,score:64,top3mass:.69,margin:.02,
   winnerConfidence:.55,winnerStable:false,scenarioProb:.43,
   evidence:.55,readiness:{prediction:.84},...overrides};
 return w.ARVEXQMorningTicketLanes.classify({circuit:'地方'},{rows,coverage:.70},audit);
}
const place=laneTest();
assert(place.selected&&place.types.includes('的中重視型'));
assert(!place.types.includes('勝ち馬明確型'),'P2/P3 stable without dominant winner');
const winner=laneTest({selected:true,winnerStable:true,winnerConfidence:.81,margin:.075,score:84});
assert(winner.selected&&winner.primaryType==='勝ち馬明確型');
const longshot=laneTest({winnerStable:true,winnerConfidence:.70,margin:.027,score:73});
assert(longshot.types.includes('高配当狙い型'));
assert(!('hitRate' in longshot)&&!('expectedValue' in longshot));
assert(!laneTest({readiness:{prediction:.1}}).selected);
// Public selection is allowed only when a real, non-skipped buy exists.
const winnerSelection={...winner,selected:true};
const accepted=w.ARVEXQMorningTicketLanes.requireMorningTickets(winnerSelection,{
 decision:'通常買い',betInputGate:{ready:true},
 items:[{level:'本線',kind:'馬連',combos:[[1,2],[1,3]]},
        {level:'3連単チャレンジ',kind:'3連単',combos:[[1,2,3]]}]
});
assert.equal(accepted.selected,true);
assert.deepEqual(accepted.ticketKinds,['馬連'],'a one-point trifecta is not a valid 6–12 ticket challenge');
assert.match(accepted.reason,/朝の買い目成立/);
assert.equal(accepted.primaryType,'的中重視型',
  'a place-compatible ticket retains its morning place type');
const wrongKind=w.ARVEXQMorningTicketLanes.requireMorningTickets(
 {...winner,selected:true,types:['勝ち馬明確型'],primaryType:'勝ち馬明確型'},{
 decision:'通常買い',betInputGate:{ready:true},
 items:[{level:'本線',kind:'ワイド',combos:[[1,2]]}]
});
assert.equal(wrongKind.selected,false,'wide alone must not claim clear winner');
assert.deepEqual(wrongKind.types,[]);
const noTrifecta=w.ARVEXQMorningTicketLanes.requireMorningTickets(
 {...longshot,selected:true,types:['高配当狙い型'],primaryType:'高配当狙い型'},{
 decision:'通常買い',betInputGate:{ready:true},
 items:[{level:'本線',kind:'馬連',combos:[[1,2]]}]
});
assert.equal(noTrifecta.selected,false,'no high-payout type when trifecta is skipped');
for(const rejected of [
  null,
  {decision:'見送り',betInputGate:{ready:true},items:[{level:'本線',kind:'ワイド',combos:[[1,2]]}]},
  {decision:'通常買い',betInputGate:{ready:false},items:[{level:'本線',kind:'ワイド',combos:[[1,2]]}]},
  {decision:'通常買い',betInputGate:{ready:true},items:[]},
  {decision:'通常買い',betInputGate:{ready:true},items:[{level:'本線',kind:'ワイド',combos:[[1,1]]}]},
  {decision:'通常買い',betInputGate:{ready:true},items:[{level:'3連単チャレンジ',kind:'3連単',combos:[[1,2,3]]}]}
]){
 assert.equal(w.ARVEXQMorningTicketLanes.requireMorningTickets(winnerSelection,rejected).selected,false);
}
const onlyPlace=w.ARVEXQMorningTicketLanes.qualifyPlaceBet(
 {selectionAudit:{selected:false,score:64}},
 {_arvexqMorningLaneCandidate:place},null);
assert.equal(onlyPlace.selectionAudit.selected,true,
 'an approved place lane can enter the independent unordered-ticket gate');
assert.equal(onlyPlace.selectionAudit.morningPlaceLane,true);
assert.equal(w.ARVEXQMorningTicketLanes.qualifyPlaceBet(
 {selectionAudit:{selected:false}}, {_arvexqMorningLaneCandidate:laneTest({readiness:{prediction:.1}})},null)
 .selectionAudit.selected,false,'unqualified place cannot bypass strict selection');
assert.equal(w.ARVEXQMorningTicketLanes.hasMorningPlace({},{
 selected:true,types:['的中重視型']}),true,'frozen morning place lane remains eligible pre-off');
console.log('MORNING_THREE_LANES_AND_ACTIONABLE_TICKET_GATE_OK');
