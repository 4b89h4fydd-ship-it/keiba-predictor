import assert from 'node:assert/strict';
import {test} from 'node:test';
import worker from '../worker-entry.js';
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
