/* Executable contract for immutable morning horses + ticket combinations. */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs');
const w={};
new Function('window',fs.readFileSync('arvexq/ui/static/morning/frozen_ticket_evidence.js','utf8'))(w);
const src=w.ARVEXQMorningEvidence;
const race={id:'nar-2026-10-11-高知-04',date:'2026-10-11',startTime:'17:30',circuit:'地方'};
const marks=Array.from({length:8},(_,i)=>({
 horse:{horseNumber:i+1,name:'Horse '+(i+1)},predMark:i===0?'◎':i===1?'○':i===2?'▲':'△',
 singleWinSuitable:i===0}));
const plan={decision:'通常買い',betInputGate:{ready:true},engineVersion:'unmodified-frozen-test',
 items:[{level:'本線',kind:'ワイド',combos:[[1,2],[1,3]],reason:'observed role strength'}]};
const selection={selected:true,primaryType:'的中重視型',types:['的中重視型'],ticketKinds:['ワイド']};
const payload=src.capture(race,{rows:marks},plan,selection);
assert(payload,'capture should accept real complete ticket');
payload.fixedAt='2026-10-11T06:25:00+09:00';
assert(src.verify(race,payload));
const frozen=src.sealedPlan(race,payload);
assert.equal(frozen.items[0].kind,'ワイド');
assert.deepEqual(frozen.items[0].combos,[[1,2],[1,3]]);
assert.equal(frozen.items[0].level,'本線');
assert.equal(frozen.fixedAt,payload.fixedAt);
assert.equal(frozen.primaryKind,'ワイド');
assert.equal(payload.axisHorseNumber,1);
assert.equal(frozen.items[0].reason,'observed role strength');
marks[0].predMark='○';plan.items[0].combos[0][0]=8;
assert.equal(payload.marks[0].mark,'◎','source mark changes must not alter frozen original');
assert.deepEqual(payload.items[0].combos,[[1,2],[1,3]],'source ticket changes must not alter frozen original');
frozen.items[0].combos[0][0]=7;
assert.deepEqual(payload.items[0].combos,[[1,2],[1,3]],'rendered plan must not alter original');
const invalid=[{...payload,fixedAt:'2026-10-11T18:00:00+09:00'},
 {...payload,raceId:'another-race'},
 {...payload,items:[{level:'本線',kind:'ワイド',combos:[[1,99]]}]},
 {...payload,marks:payload.marks.slice(0,3)}];
for(const d of invalid)assert(!src.verify(race,d),'invalid or late pre-off evidence rejected');
const withoutAxisMarks=marks.map((x,i)=>({...x,predMark:i===0?'○':i===1?'▲':'△'}));
const noAxis=src.capture(race,{rows:withoutAxisMarks},plan,selection);
assert(noAxis&&noAxis.axisStatus==='no-axis','no ◎ must remain explicit');
noAxis.fixedAt=payload.fixedAt;
assert(src.verify(race,noAxis));
assert.equal(src.sealedPlan(race,noAxis).noAxis,true);
const improper=src.capture(race,{rows:withoutAxisMarks},plan,
 {...selection,primaryType:'勝ち馬明確型'});
assert.equal(improper,null,'never invent a win-axis where no ◎ exists');
const ordered=src.capture(race,{rows:withoutAxisMarks},{
 ...plan,items:[{level:'本線',kind:'馬単',combos:[[1,2]]}]},
 {...selection,ticketKinds:['馬単']});
assert.equal(ordered,null,'no-axis cannot promote ordered winner tickets');
console.log('IMMUTABLE_MORNING_MARKS_AND_REAL_TICKET_COMBOS_PASS');
