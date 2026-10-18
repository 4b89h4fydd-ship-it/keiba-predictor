'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const context={};context.window=context;vm.createContext(context);
function load(p){vm.runInContext(fs.readFileSync(p,'utf8'),context,{filename:p});}
load('arvexq/ui/static/morning/frozen_ticket_evidence.js');
for(const name of ['prediction','marks','tickets','prediction_frame','mark_frame','ticket_frame'])
  load('arvexq/ui/static/forecast/'+name+'.js');

const triples=[[1,2,3],[1,3,2],[2,1,3],[2,3,1],[3,1,2],[3,2,1]];
const receipt={
 version:'arvexq-morning-ticket-evidence-v1',
 raceId:'jra-2099-12-31-阪神-11',raceDate:'2099-12-31',
 fixedAt:'2099-12-31T09:10:00+09:00',axisStatus:'honmei',axisHorseNumber:1,
 marks:[{horseNumber:1,mark:'◎'},{horseNumber:2,mark:'○'},
   {horseNumber:3,mark:'▲'},{horseNumber:4,mark:'△'},{horseNumber:5,mark:'☆'}],
 items:[
   {level:'本線',kind:'馬連',combos:[[1,2],[1,3]],reason:'専門紙原本'},
   {level:'3連単チャレンジ',kind:'3連単',combos:triples,reason:'<unsafe>'}
 ],
 ticketKinds:['馬連','3連単'],modelVersion:'approved-recorded-original'
};
const race={
 id:receipt.raceId,date:receipt.raceDate,startTime:'23:50',
 horses:receipt.marks.map((m)=>({horseNumber:m.horseNumber,name:'Horse '+m.horseNumber})),
 morningTicketEvidence:receipt
};
const original=JSON.stringify(race);
assert.equal(context.ARVEXQMorningEvidence.verify(race,receipt),true);
const shown=context.ARVEXQProductionTickets.build(race);
assert.equal(shown.fixedAt,receipt.fixedAt);
assert.equal(shown.items.length,2);
assert.equal(JSON.stringify(shown.items[0].combos),JSON.stringify([[1,2],[1,3]]));
assert.equal(JSON.stringify(shown.items[1].combos),JSON.stringify(triples));
const frame=context.ARVEXQTicketFrame.contents(race);
assert.match(frame,/おすすめ買い目/);
assert.match(frame,/1 - 2/);
assert.match(frame,/3 - 2 - 1/);
assert.match(frame,/8点|2点/);
assert.doesNotMatch(frame,/<unsafe>/);
assert.equal(JSON.stringify(race),original);

for(const malformed of [
  {...race, id:'different-race'},
  {...race,date:'2099-12-30'},
  {...race, morningTicketEvidence:{...receipt,fixedAt:'2100-01-01T00:00:00+09:00'}},
  {...race, morningTicketEvidence:{...receipt,items:[{level:'本線',kind:'馬連',combos:[[1,99]]}],ticketKinds:['馬連']}},
  {...race,morningTicketEvidence:null}
]){
 const item=context.ARVEXQProductionTickets.build(malformed);
 assert.equal(item.items.length,0);
 assert.doesNotMatch(context.ARVEXQTicketFrame.render(malformed),/3 - 2 - 1/);
}

 // Historical 2026-10-18 races must show ONLY their actual pre-off originals.
 // Exercise the same adapter for 92 distinct race IDs, not only selected UI cards.
const originalDay='2026-10-18';
for(let k=0;k<92;k++){
  const id=(k%2?'nar':'jra')+'-2026-10-18-venue'+k+'-race'+k;
  const fixed={...receipt,raceId:id,raceDate:originalDay,fixedAt:'2026-10-18T07:10:00+09:00'};
  const originalRace={...race,id,date:originalDay,startTime:'12:00',circuit:k%2?'地方':'中央',
    morningTicketEvidence:fixed};
  assert.equal(context.ARVEXQMorningEvidence.verify(originalRace,fixed),true);
  const preserved=context.ARVEXQProductionPrediction.build(originalRace);
  assert.equal(context.ARVEXQProductionPrediction.current().source,'saved-preoff');
  assert.deepEqual(Array.from(preserved.rows,x=>x.predMark),['◎','○','▲','△','☆']);
  assert.equal(context.ARVEXQProductionMarks.visible(preserved.rows[0]),'◎');
  assert.equal(preserved.rows[0].winProbability,null);
  assert.match(context.ARVEXQMarkFrame.render(),/発走前の保存原本/);
  assert.match(context.ARVEXQPredictionFrame.render(),/発走前に保存された予想印/);
  const bet=context.ARVEXQProductionTickets.current();
  assert.equal(bet.items.length,2);
  assert.equal(JSON.stringify(bet.items[1].combos),JSON.stringify(triples));
}
// The same verified archive is allowed in existing nested daily summaries.
const nestedEvidence={...receipt,raceId:'test-nested-2026-10-18',raceDate:originalDay,
 fixedAt:'2026-10-18T07:10:00+09:00'};
const nestedRace={...race,id:nestedEvidence.raceId,date:originalDay,startTime:'12:00',
 morningTicketEvidence:null,
 volatility:{morningPicks:{ticketEvidence:nestedEvidence}}};
assert.equal(context.ARVEXQProductionPrediction.build(nestedRace).rows[0].predMark,'◎');
assert.equal(context.ARVEXQProductionTickets.build(nestedRace).items.length,2);
// No saved original, wrong roster or a receipt sealed after the post: no historical marks.
for(const bad of [
 {...nestedRace,volatility:{}},
 {...nestedRace,horses:nestedRace.horses.slice(1)},
 {...nestedRace,volatility:{morningPicks:{ticketEvidence:{
    ...nestedEvidence,fixedAt:'2026-10-18T12:10:00+09:00'}}}},
 {...nestedRace,id:'another-race'},
]){
 const row=context.ARVEXQProductionPrediction.build(bad).rows[0];
 assert.equal(row.predMark,'');
 assert.equal(context.ARVEXQProductionTickets.build(bad).items.length,0);
}

console.log('VERIFIED_ORIGINAL_TICKETS_RENDERED_UNCHANGED_AND_INVALIDS_REJECTED');
