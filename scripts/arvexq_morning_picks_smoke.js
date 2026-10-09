#!/usr/bin/env node
// A late odds update, changed AI scores, or result publication must never
// reshuffle the morning's selected/special race list.
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs');
const src=fs.readFileSync('arvexq/ui/static/app.js','utf8');
function take(name){
  const a=src.lastIndexOf('function '+name+'('),b=src.indexOf('\n}',a);
  assert(a>=0&&b>a,'missing '+name);
  return src.slice(a,b+2);
}
const code=['morningPickOf','morningPickReady','selectedRaceCandidates','specialForecastRaceCandidates']
  .map(take).join('\n')+'\nreturn {morningPickReady,selectedRaceCandidates,specialForecastRaceCandidates};';
const state={races:[
  {id:'one',date:'2026-10-10',circuit:'中央',track:'東京',raceNumber:1,startTime:'10:00',morningPickVersion:'v1',morningPickFixedAt:'2026-10-10T06:30:00+09:00',morningSelected:true,morningSelectedScore:86,morningSpecial:false,
     morningPrimaryType:'的中重視型',morningSelectedTypes:['的中重視型'],morningSelectionReason:'朝の固定分類',morningTicketKinds:['ワイド']},
  {id:'two',date:'2026-10-10',circuit:'地方',track:'高知',raceNumber:12,startTime:'20:30',morningPickVersion:'v1',morningPickFixedAt:'2026-10-10T06:30:00+09:00',morningSelected:false,morningSelectedScore:0,morningSpecial:true},
  {id:'three',date:'2026-10-10',circuit:'地方',track:'大井',raceNumber:5,startTime:'15:00',morningPickVersion:'v1',morningPickFixedAt:'2026-10-10T06:30:00+09:00',morningSelected:false,morningSpecial:false},
]};
const helper=new Function('state','n','raceChronologicalCompare',code);
const api=helper(state,(v,d=0)=>Number.isFinite(Number(v))?Number(v):d,(a,b)=>a.raceNumber-b.raceNumber);
assert(api.morningPickReady());
assert.deepEqual(api.selectedRaceCandidates().map(x=>x.race.id),['one']);
assert.equal(api.selectedRaceCandidates()[0].selection.primaryType,'的中重視型');
assert.deepEqual(api.selectedRaceCandidates()[0].selection.ticketKinds,['ワイド']);
assert.deepEqual(api.specialForecastRaceCandidates().map(x=>x.id),['two']);
state.races[0].winOdds=160;state.races[0].raceStatus='確定';
state.races[1].title='レース名訂正';state.races[2].volatility={label:'荒'};
state.races[2].integratedEvaluation={score:99,mark:'◎'};
assert.deepEqual(api.selectedRaceCandidates().map(x=>x.race.id),['one']);
assert.deepEqual(api.specialForecastRaceCandidates().map(x=>x.id),['two']);
state.races.push({id:'late',circuit:'中央',raceNumber:11,startTime:'15:45'});
assert.deepEqual(api.selectedRaceCandidates().map(x=>x.race.id),['one']);
assert.deepEqual(api.specialForecastRaceCandidates().map(x=>x.id),['two']);
for (const r of state.races) {
  delete r.morningPickVersion;delete r.morningPickFixedAt;
}
assert.equal(api.morningPickReady(),false);
assert.equal(api.selectedRaceCandidates().length,0);
assert.equal(api.specialForecastRaceCandidates().length,0);
console.log('MORNING_PICK_IMMUTABLE_AND_NO_LATE_ADDITION_PASS');
