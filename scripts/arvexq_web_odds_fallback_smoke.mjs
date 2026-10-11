// A source outage is reported as missing data, never a fictitious acquired price.
import assert from 'node:assert/strict';
import worker from '../workers/web.mjs';

const id='nar-2026-10-11-佐賀-09',date='2026-10-11';
const source={id,date,circuit:'地方',track:'佐賀',raceNumber:9,
  horses:[{horseNumber:1,name:'検証馬A'},{horseNumber:2,name:'検証馬B'}]};
const env={ASSETS:{async fetch(request){
  const path=new URL(request.url).pathname;
  if(path==='/odds-sources/'+date+'.json')
    return Response.json({version:'arvexq-odds-sources-v1',date,races:{[id]:source}});
  return new Response('not found',{status:404});
}}};
let attempts=0;
globalThis.fetch=async request=>{
  assert.ok(String(request).startsWith('https://www.keiba.go.jp/'));
  attempts++;
  return new Response('source unavailable',{status:503});
};
globalThis.caches={default:{match:async()=>null,put:async()=>{}}};
const ctx={waitUntil(){}},root='https://example.invalid/api/live-odds/';
for(const suffix of ['', '?force=1']){
  const response=await worker.fetch(new Request(root+encodeURIComponent(id)+suffix),env,ctx);
  assert.equal(response.status,200,'known race responds with explicit missingness');
  assert.equal(response.headers.get('cache-control'),'no-store');
  const body=await response.json();
  assert.equal(body.ok,false);
  assert.equal(body.race_id,id);
  assert.equal(body.oddsStatus,'unavailable');
  assert.equal(body.refreshFailed,true);
  assert.deepEqual(body.odds,[],'never manufacture odds');
}
assert.equal(attempts,2,'manual refresh retries the primary source');
const absent=await worker.fetch(new Request(root+encodeURIComponent('nar-2026-10-11-架空-01')),env,ctx);
assert.equal(absent.status,404,'unknown race is not a valid availability response');
console.log('WEB_ODDS_UNAVAILABLE_AND_MANUAL_RETRY_PASS');
