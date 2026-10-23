import test from 'node:test';
import assert from 'node:assert/strict';
import {publicRace, publicRaceResponse} from '../public-race.js';

const fixture={ok:true,detail:{id:'nar-test',date:'2026-10-17',condition:'重',
  horses:[{horseNumber:1,name:'馬',winOdds:2.5,recentRaces:[{finish:1}],mark:'◎',integratedEvaluation:{score:99}}],
  preRacePrediction:{horses:[{horseNumber:1,mark:'◎'}]},preRaceBet:{tickets:[[1,2,3]]},
  forecastRevisions:[{mark:'◎'}],currentForecastRevisionId:'old',
  raceCardView:[{name:'馬',mark:'◎'}],result:{status:'確定',payouts:[{type:'単勝',amount:250}]}},odds:[{horse_no:1,win_odds:2.5}]};
test('stored legacy opinions cannot become active, factual data and originals survive',()=>{
 const before=JSON.stringify(fixture),projected=publicRace(fixture);
 assert.equal(projected.detail.predictionStatus,'disabled');
 for(const key of ['preRacePrediction','preRaceBet','forecastRevisions','currentForecastRevisionId'])assert(!(key in projected.detail));
 assert(!('mark' in projected.detail.horses[0]));assert(!('mark' in projected.detail.raceCardView[0]));
 assert.deepEqual(projected.detail.result,fixture.detail.result);assert.deepEqual(projected.odds,fixture.odds);
 assert.deepEqual(projected.detail.horses[0].recentRaces,fixture.detail.horses[0].recentRaces);
 assert.equal(JSON.stringify(fixture),before);
});
for(const path of ['/api/race/nar-test','/api/race/nar-test?view=display','/api/racecard/nar-test','/api/day?date=2026-10-17&details=1'])test('public boundary '+path,async()=>{
 const request=new Request('https://example.test'+path);
 const response=await publicRaceResponse(Response.json(fixture,{headers:{etag:'old','content-length':'123'}}),request);
 const body=await response.json();assert.equal(body.detail.predictionStatus,'disabled');
 assert.equal(response.headers.get('etag'),null);assert.equal(response.headers.get('content-length'),null);
 assert.equal(response.headers.get('cache-control'),'no-store');
});
test('authenticated audit and write paths retain immutable originals',async()=>{
 for(const [path,method] of [['/api/admin/snapshot-export','GET'],['/api/sync','POST']]){
  const response=Response.json(fixture),request=new Request('https://example.test'+path,{method});
  assert.equal(await publicRaceResponse(response,request),response);
 }
});
test('plain errors and non-JSON responses are preserved',async()=>{
 const request=new Request('https://example.test/api/day');
 for(const response of [new Response('down',{status:503}),new Response('unavailable')])assert.equal(await publicRaceResponse(response,request),response);
});

test('existing Stage64 preoff products survive public API projection without recalculation', async()=>{
 const race={id:'nar-2026-10-23-園田-11',date:'2026-10-23',predictionStatus:'ready',
  prediction:{raceId:'nar-2026-10-23-園田-11',date:'2026-10-23',predictionStatus:'ready',productionEligible:true,
   modelVersion:'arvexq-stage64-product-v1',stages:{marks:{value:{orderedWinCandidates:[1,2,3,4,5]}}}},
  horses:[1,2,3,4,5,6].map(n=>({horseNumber:n,name:'馬'+n,recentRaces:[{finish:n}]})),
  predictionMarks:['◎','○','▲','△','☆'].map((mark,i)=>({horseNumber:i+1,mark,winProbability:0.1})),
  recommendedBets:[{type:'ワイド',horses:[1,2]}]};
 const source={ok:true,detail:race};
 const response=await publicRaceResponse(Response.json(source),new Request('https://example.test/api/race/nar-2026-10-23-園田-11?view=display'));
 const detail=(await response.json()).detail;
 assert.equal(detail.predictionStatus,'ready');
 assert.deepEqual(detail.predictionMarks.map(m=>m.mark),['◎','○','▲','△','☆']);
 assert.deepEqual(detail.horses.slice(0,5).map(h=>h.predMark),['◎','○','▲','△','☆']);
 assert.deepEqual(detail.recommendedBets,race.recommendedBets);
 assert.deepEqual(detail.horses[0].recentRaces,race.horses[0].recentRaces);
 assert.equal(race.horses[0].predMark,undefined);
});
test('unverified or mismatched Stage64 cannot appear as live marks',()=>{
 const race={id:'nar-test',date:'2026-10-23',predictionStatus:'ready',
  prediction:{raceId:'nar-test',date:'2026-10-23',predictionStatus:'ready',productionEligible:true,
    modelVersion:'arvexq-stage64-product-v1'},
  horses:[1,2,3,4,5].map(horseNumber=>({horseNumber})),
  predictionMarks:['◎','○','▲','△','☆'].map((mark,i)=>({horseNumber:i+1,mark}))};
 for(const mutate of [r=>{r.prediction.productionEligible=false},
   r=>{r.predictionMarks[0].mark='';},
   r=>{r.predictionMarks[1].horseNumber=1},
   r=>{r.prediction.raceId='wrong'},
   r=>{r.prediction.modelVersion='retired'}]){
   const item=structuredClone(race);mutate(item);
   const result=publicRace(item);
   assert.equal(result.predictionStatus,'disabled');
   assert.equal(result.predictionMarks,undefined);
   assert.equal(result.prediction,undefined);
   assert.ok(result.horses.every(h=>!('predMark' in h)));
 }
});
