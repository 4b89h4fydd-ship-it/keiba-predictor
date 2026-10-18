import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {gzipSync} from 'node:zlib';
import {verifyCareerReadback} from '../scripts/verify-career-readback.mjs';

function envelope(value, key) {
  const raw=Buffer.from(JSON.stringify(value));
  return {bytes:raw.length,sha256:createHash('sha256').update(raw).digest('hex'),
    [key]:gzipSync(raw).toString('base64')};
}
function fixture() {
  const raceId='nar-2026-10-15-名古屋-01';
  const archive={...envelope([{date:'2026-09-01',finish:2}], 'payload'),
    encoding:'arvexq-career-gzip-json-v2',priorRaceDate:'2026-10-15',
    includesRecent:true,storedRunCount:1};
  const original={id:raceId,date:'2026-10-15',horses:[{horseNumber:2,careerArchive:archive}]};
  const full={...envelope(original,'gzipBase64'),version:'arvexq-full-payload-v1'};
  return {ok:true,detail:{id:raceId,horses:[{horseNumber:2}],arvexqFullPayload:full}};
}
test('restores and validates a career archive inside the full saved original',()=>{
  const body=fixture();
  const result=verifyCareerReadback(body,body.detail.id,2);
  assert.equal(result.storedRuns,1);
  assert.equal(result.restoredFullPayload,true);
  assert.equal(body.detail.horses[0].careerArchive,undefined);
});
test('rejects corrupt full originals before trusting nested observations',()=>{
  const body=fixture();body.detail.arvexqFullPayload.sha256='0'.repeat(64);
  assert.throws(()=>verifyCareerReadback(body,body.detail.id,2),/digest mismatch/);
});
test('rejects a different race restored behind the requested compact identity',()=>{
  const body=fixture();body.detail.id='another-race';
  assert.throws(()=>verifyCareerReadback(body,'another-race',2),/restored race identity mismatch/);
});
test('retains missing-career failure for a saved original without an archive',()=>{
  const body={ok:true,detail:{id:'race',date:'2026-10-15',horses:[{horseNumber:2}]}};
  assert.throws(()=>verifyCareerReadback(body,'race',2),/career archive missing/);
});
