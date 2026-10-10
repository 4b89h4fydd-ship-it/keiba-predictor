import assert from 'node:assert/strict';
import {validateSavedOdds} from '../workers/saved_odds.mjs';
import worker from '../workers/web.mjs';
const source={id:'race',sourceSnapshotSha256:'a'.repeat(64),horses:[{horseNumber:1,name:'原本'}]};
const data={ok:true,race_id:'race',sourceSnapshotSha256:source.sourceSnapshotSha256,oddsUpdatedAt:'2026-10-10T08:40:00+09:00',odds:[{horse_no:1,horse_name:'原本',win_odds:4.3,popularity:2,oddsSource:'netkeiba'}]};
const saved=validateSavedOdds(data,source);
assert(saved&&saved.refreshFailed&&saved.oddsStatus==='saved');assert.equal(saved.oddsUpdatedAt,data.oddsUpdatedAt);
assert.equal(validateSavedOdds({...data,race_id:'other'},source),null);
assert.equal(validateSavedOdds({...data,odds:[{...data.odds[0],horse_name:'別馬'}]},source),null);
assert.equal(validateSavedOdds({...data,sourceSnapshotSha256:'b'.repeat(64)},source),null);
assert.equal(validateSavedOdds({...data,odds:[{...data.odds[0],oddsSource:'model'}]},source),null);
console.log('ACQUIRED_SAVED_ODDS_OUTAGE_EXACT_TIME_NO_FORECAST_NO_WRONG_RUNNER_PASS');
const id='jra-2026-10-10-京都-01';
const productionSource={...source,id,date:'2026-10-10',circuit:'中央',netkeibaRaceId:'202608040101'};
const backup={...data,race_id:id};
globalThis.caches={default:{async match(){return null},async put(){throw Error('outage must not cache invented live prices')}}};
const originalFetch=globalThis.fetch;
globalThis.fetch=async()=>{throw Error('real source outage')};
const env={ASSETS:{async fetch(request){
 assert.doesNotMatch(request.url,/kraiz-api/,'fallback must be independent of D1');
 return Response.json(request.url.includes('/odds-sources/')?
   {version:'arvexq-odds-sources-v1',date:'2026-10-10',races:{[id]:productionSource}}:
   {version:'arvexq-saved-actual-odds-v1',date:'2026-10-10',races:{[id]:backup}});
}}};
try{
 const response=await worker.fetch(new Request('https://site/api/live-odds/'+encodeURIComponent(id)+'?force=1'),env,{waitUntil(){}});
 assert.equal(response.status,200);
 const body=await response.json();assert.equal(body.oddsStatus,'saved');assert.equal(body.oddsUpdatedAt,data.oddsUpdatedAt);
 assert.equal(body.odds[0].win_odds,4.3);assert.equal(body.refreshFailed,true);
 console.log('WEB_WORKER_MANUAL_REFRESH_SOURCE_OUTAGE_D1_INDEPENDENT_SAVED_ACTUAL_TIME_PASS');
}finally{globalThis.fetch=originalFetch}
