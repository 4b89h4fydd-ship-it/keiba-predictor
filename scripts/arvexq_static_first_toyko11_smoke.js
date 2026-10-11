'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const app=fs.readFileSync('arvexq/ui/static/app.js','utf8');
const data=JSON.parse(fs.readFileSync('arvexq/ui/static/racecards/2026-10-11.json','utf8'));
const staticSrc=fs.readFileSync('arvexq/ui/static/research/static_racecard.js','utf8');
const windowMock={};new Function('window',staticSrc)(windowMock);
const rid='jra-2026-10-11-東京-11';
const record=data.races.find(r=>r.id===rid);
assert.equal(record.horses.length,16,'Tokyo 11 must have complete static runner identities');
const begin=app.indexOf('function hydrateStaticRacecardFirst(');
const end=app.indexOf('function fetchRacecardOnly(',begin);
assert(begin>0&&end>begin);
const snippet=app.slice(begin,end);
const trace=[];
const state={date:'2026-10-11',detailSeq:1,race:{id:rid,date:'2026-10-11',horses:[]}};
let renders=0;
const dependencies={
 state,window:windowMock,
 edgeFetchJson:async path=>{
  assert.equal(path,'/racecards/2026-10-11.json');
  return data;
 },
 entryDataAvailable:d=>!!(d&&Array.isArray(d.horses)&&d.horses.length),
 applySummaryEnvironment:d=>d,
 mergeRaceReflection:(base,incoming)=>Object.assign({},base,incoming),
 saveDetailCache:()=>{},
 updateDetailSections:()=>{},
 traceRaceDetail:(id,event,detail)=>trace.push({id,event,detail}),
 render:()=>{renders++},
 instantTrackDetails:{}
};
const hydrate=new Function(...Object.keys(dependencies),snippet+';return hydrateStaticRacecardFirst;')(...Object.values(dependencies));
(async()=>{
 assert(app.includes('hydrateStaticRacecardFirst(id,seq,initial);'),'race-opening path must start independent roster request');
 assert.equal(await hydrate(rid,1,state.race),true);
 assert.equal(state.race.horses.length,16);
 assert.equal(state.race.horses[0].name,'ニシノティアモ');
 assert.equal(state.race._entryOnly,true,'a factual racecard must not pretend to be a complete analysis');
 assert.equal(state.race._staticRacecardFallback,true);
 assert.equal(trace[0].event,'racecard-static-first');
 assert.equal(renders,1);
 const original=state.race;
 assert.equal(await hydrate(rid,1,original),false,'full roster must not be replaced by another sparse copy');
 assert.equal(state.race,original);
 state.detailSeq=2;
 state.race={id:'jra-2026-10-11-東京-12',date:'2026-10-11',horses:[]};
 assert.equal(await hydrate(rid,1,{date:'2026-10-11'}),false,'stale requests cannot overwrite the newly opened race');
 assert.equal(state.race.id,'jra-2026-10-11-東京-12');
 console.log('TOKYO11_STATIC_FIRST_16_RUNNERS_AND_STALE_PROTECTION_PASS');
})().catch(e=>{console.error(e);process.exitCode=1});
