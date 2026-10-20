import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {gzipSync,gunzipSync} from 'node:zlib';
import {webcrypto} from 'node:crypto';
import worker from '../workers/api.mjs';
import {enhanceNarGoingResponse} from '../workers/nar_going_moisture.mjs';
globalThis.crypto??=webcrypto;
// Known non-Banei routes must stream the original response without even
// cloning it. This is a resource boundary, not a different prediction path.
for(const id of ['jra-2026-10-18-東京-11','nar-2026-10-20-金沢-03']){
 const response=new Response('{"detail":{"originalNumber":1.0}}');
 response.clone=()=>{throw Error('non-Banei archive was cloned')};
 assert.equal(await enhanceNarGoingResponse(response,()=>{throw Error('unexpected fetch')},id),response);
 assert.equal(await response.text(),'{"detail":{"originalNumber":1.0}}');
}
// The established Banei-only correction still works on its existing source.
let fetches=0;
const banei=new Response(JSON.stringify({detail:{id:'nar-2026-10-18-帯広ば-01',condition:'不明',horses:[]}}));
const corrected=await enhanceNarGoingResponse(banei,async url=>{fetches++;assert.match(url,/keiba\.go\.jp\/KeibaWeb\/TodayRaceInfo\/RaceMarkTable/);return new Response(' 馬場：2.3')},'nar-2026-10-18-帯広ば-01');
assert.equal((await corrected.json()).detail.goingMoisture,'2.3');assert.equal(fetches,1);
const unchanged=new Response('{"detail":{"id":"nar-2026-10-18-帯広ば-01","condition":"良","originalNumber":1.0}}');
assert.equal(await enhanceNarGoingResponse(unchanged,()=>{throw Error('known going must not fetch')}),unchanged);
let checked=0,nonBanei=0,baneiCount=0,bytes=0,maxBytes=0;
for(const day of ['2026-10-16','2026-10-18']){
 const directory='arvexq/ui/static/saved-snapshots';
 const manifest=JSON.parse(fs.readFileSync(path.join(directory,day+'.json')));
 for(const [id,ref] of Object.entries(manifest.races)){
  const archive=JSON.parse(fs.readFileSync(path.join(directory,ref.file)));
  const raw=gunzipSync(Buffer.from(archive.gzipBase64,'base64'));
  const detail=JSON.parse(raw);
  const isBanei=['帯広','帯広ば'].includes(detail.track);
  assert.equal(detail.id,id);
  const sha=Buffer.from(await crypto.subtle.digest('SHA-256',raw)).toString('hex');
  const envelope={arvexqFullPayload:{version:'arvexq-full-payload-v1',bytes:raw.length,sha256:sha,gzipBase64:gzipSync(raw).toString('base64')}};
  const DB={prepare(sql){assert.match(sql,/^SELECT /);return{bind(raceId){assert.equal(raceId,id);return this},async first(){if(sql.includes('FROM race_summaries'))return null;return {codec:'arvexq-full-payload-v1',payload:JSON.stringify(envelope),analysis_ready:1,updated_at:123}},async all(){return {results:[]}}}}};
  const clone=Response.prototype.clone,originalFetch=globalThis.fetch;let clones=0;
  globalThis.fetch=async url=>{assert(isBanei);assert.match(String(url),/keiba\.go\.jp\/KeibaWeb\/TodayRaceInfo\/RaceMarkTable/);return new Response('',{status:503})};
  Response.prototype.clone=function(){clones++;return clone.call(this)};
  try{
   const response=await worker.fetch(new Request('https://api.test/api/race/'+encodeURIComponent(id)+'?view=display'),{DB},{});
   assert.equal(response.status,isBanei?404:200,id);
   const restored=await response.text();
   if(!isBanei)assert(restored.endsWith(',"detail":'+raw.toString()+'}'),id+' must preserve exact original JSON bytes');
   assert.equal(clones,0,id+' must not clone an excluded or non-Banei archive');
   if(isBanei)baneiCount++;else nonBanei++;
   checked++;bytes+=raw.length;maxBytes=Math.max(maxBytes,raw.length);
  }finally{Response.prototype.clone=clone;globalThis.fetch=originalFetch}
 }
}
console.log('WORKER_RESOURCE_GUARD_REAL_ARCHIVES_PASS '+JSON.stringify({checked,nonBanei,banei:baneiCount,bytes,maxBytes,unexpectedArchiveClones:0,sqlWrites:0}));
