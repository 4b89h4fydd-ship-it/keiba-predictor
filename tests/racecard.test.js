import assert from 'node:assert/strict';
import {test} from 'node:test';
import worker from '../worker-entry.js';
import {gzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {restoreDisplaySnapshot} from '../racecard.js';
const id='nar-2026-10-07-大井-11';
const req=()=>new Request('https://arvexq.test/api/racecard/'+encodeURIComponent(id));
function db(mode='loaded'){
 const queries=[];
 return {queries,prepare(sql){
  assert.ok(!/odds_current|UPDATE|INSERT|DELETE/.test(sql));queries.push(sql);
  return {bind(value){assert.equal(value,id);return this},async first(){
   if(mode==='error')throw Error('unavailable');
   if(mode==='missing')return null;
   return {basic:JSON.stringify({id,track:'大井',fieldSize:mode==='empty'?0:16})}
  },async all(){return {results:mode==='empty'?[]:[{horse:JSON.stringify({horseNumber:1,name:'テスト馬',scratched:1})}]}}}
 }}
}
for(const [mode,status,entry] of [['loaded',200,'loaded'],['empty',200,'empty'],['missing',404],['error',503]]){
 test('compact racecard '+mode,async()=>{const DB=db(mode),response=await worker.fetch(req(),{DB},{});assert.equal(response.status,status);assert.equal(response.headers.get('access-control-allow-origin'),'*');const body=await response.json();assert.equal(body.race_id,id);if(entry){assert.equal(body.entry_state,entry);assert.equal(body.detail._entryOnly,true);assert.ok(!('allPastRuns' in (body.detail.horses[0]||{})));if(mode==='loaded')assert.equal(body.detail.horses[0].scratched,true)}})
}
test('Safari preflight',async()=>{const r=await worker.fetch(new Request(req(),{method:'OPTIONS',headers:{'access-control-request-headers':'cache-control,pragma'}}),{},{});assert.equal(r.status,204);assert.equal(r.headers.get('access-control-allow-headers'),'cache-control,pragma')});
test('display response removes retired prediction, retains history and tolerates odds failure',async()=>{
 const queries=[],detail={id,horses:[{horseNumber:1,name:'馬',recentRaces:[{finish:1}],integratedEvaluation:{score:0.8}}]};
 const DB={prepare(sql){queries.push(sql);return {bind(value){assert.equal(value,id);return this},async first(){return {payload:JSON.stringify(detail),analysis_ready:1,updated_at:1}},async all(){throw Error('odds unavailable')}}}};
 const r=await worker.fetch(new Request('https://arvexq.test/api/race/'+encodeURIComponent(id)+'?view=display'),{DB},{});
 assert.equal(r.status,200);const b=await r.json();assert.deepEqual(b.detail.horses[0].recentRaces,detail.horses[0].recentRaces);assert.equal(b.detail.horses[0].name,detail.horses[0].name);assert.equal(b.detail.horses[0].horseNumber,1);assert.ok(!('integratedEvaluation' in b.detail.horses[0]));assert.equal(b.detail.predictionStatus,'disabled');assert.deepEqual(detail.horses[0].integratedEvaluation,{score:0.8});assert.deepEqual(b.odds,[]);assert.equal(b.analysis_ready,true);assert.ok(queries[0].includes("json_remove(payload, '$.massFeatureSnapshot')"));
});

test('display response restores full horse histories from existing verified gzip envelope',async()=>{
 const full={id,horses:[{horseNumber:1,name:'テスト馬',recentRaces:[{date:'2026-10-01',finish:2}],allPastRuns:[{date:'2026-10-01',finish:2},{date:'2026-09-01',finish:1}]}],massFeatureSnapshot:{large:true}};
 const raw=Buffer.from(JSON.stringify(full),'utf8');
 const compact={id,horses:[{horseNumber:1,name:'テスト馬'}],arvexqFullPayload:{
  version:'arvexq-full-payload-v1',bytes:raw.length,
  sha256:createHash('sha256').update(raw).digest('hex'),gzipBase64:gzipSync(raw).toString('base64')}};
 const DB={prepare(sql){return {bind(v){assert.equal(v,id);return this},async first(){return {payload:JSON.stringify(compact),analysis_ready:1,updated_at:1}},async all(){return {results:[]}}}}};
 const response=await worker.fetch(new Request('https://arvexq.test/api/race/'+encodeURIComponent(id)+'?view=display'),{DB},{});
 assert.equal(response.status,200);
 const body=await response.json();
 assert.deepEqual(body.detail.horses[0].allPastRuns,full.horses[0].allPastRuns);
 assert.deepEqual(body.detail.horses[0].recentRaces,full.horses[0].recentRaces);
 assert.ok(!('massFeatureSnapshot' in body.detail));
 assert.equal(compact.horses[0].allPastRuns,undefined);
});
test('full-snapshot digest mismatch fails closed, never renders an empty fake history',async()=>{
 const original={id,horses:[{horseNumber:1,allPastRuns:[{finish:1}]}]};
 const raw=Buffer.from(JSON.stringify(original));
 const compact={id,horses:[{horseNumber:1}],arvexqFullPayload:{
  version:'arvexq-full-payload-v1',bytes:raw.length,sha256:'0'.repeat(64),
  gzipBase64:gzipSync(raw).toString('base64')}};
 await assert.rejects(()=>restoreDisplaySnapshot(compact),/digest mismatch/);
});
test('display keeps already expanded legacy race details unchanged',async()=>{
 const detail={id,horses:[{horseNumber:1,recentRaces:[{finish:3}]}]};
 assert.equal(await restoreDisplaySnapshot(detail),detail);
});
