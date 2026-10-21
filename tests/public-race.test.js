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

test('Stage64 six-stage ticket candidates reach the existing public API unchanged', async()=> {
  const original = {
    ok: true, detail: {
      id: 'nar-2099-01-01-高知-01', date: '2099-01-01', circuit: '地方',
      horses: [{horseNumber: 1, name: '馬A'}],
      preRacePrediction: {horses: [{horseNumber: 1, mark: '◎'}]},
      tickets: [[2, 1, 3]], recommendedBets: [{legacy: true}],
      researchShadow: {stage64: {
        raceId: 'nar-2099-01-01-高知-01', date: '2099-01-01', circuit: 'nar',
        modelVersion: 'nar-flat-shadow-v1',
        stages: {
          marks: {value: {winRole: {horseNumber: 1}, axisRole: {horseNumber: 1},
                          productMarks: null}},
          tickets: {status: 'research-only-unvalidated',
                    value: {hypotheticalTrifectaTop10: [[1, 2, 3], [1, 3, 2]],
                            recommendedBets: null}}
        }
      }}
    }
  };
  const immutable = JSON.stringify(original);
  for (const path of ['/api/race/nar-2099-01-01-高知-01?view=display',
                      '/api/day?date=2099-01-01&details=1']) {
    const request = new Request('https://example.test' + path);
    const response = await publicRaceResponse(Response.json(original), request);
    const body = await response.json();
    const stage = body.detail.researchShadow.stage64.stages;
    assert.deepEqual(stage.tickets.value.hypotheticalTrifectaTop10,
                     [[1,2,3],[1,3,2]]);
    assert.equal(stage.marks.value.winRole.horseNumber, 1);
    assert.ok(!('recommendedBets' in stage.tickets.value));
    assert.ok(!('preRacePrediction' in body.detail));
    assert.ok(!('tickets' in body.detail));
    assert.ok(!('recommendedBets' in body.detail));
  }
  assert.equal(JSON.stringify(original), immutable);
});

test('unrelated nested retired ticket keys remain unavailable',()=> {
  const data={researchShadow:{other:{stages:{tickets:{bad:true}}},
         stage64:{stages:{tickets:{value:{hypotheticalTrifectaTop10:[[1,2,3]]}}}}},
         unrelated:{tickets:[9,8,7]}};
  const projected=publicRace(data);
  assert.ok(!('tickets' in projected.researchShadow.other.stages));
  assert.ok(!('tickets' in projected.unrelated));
  assert.deepEqual(projected.researchShadow.stage64.stages.tickets.value.hypotheticalTrifectaTop10,[[1,2,3]]);
});
