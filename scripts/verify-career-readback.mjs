import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {pathToFileURL} from 'node:url';

function restore(envelope, payloadKey, budget) {
  const bytes=Number(envelope.bytes);
  assert.ok(Number.isInteger(bytes) && bytes>0 && bytes<=budget, 'invalid archive size');
  const raw=gunzipSync(Buffer.from(envelope[payloadKey], 'base64'), {maxOutputLength:budget});
  assert.equal(raw.length, bytes, 'archive byte length mismatch');
  assert.equal(createHash('sha256').update(raw).digest('hex'), envelope.sha256,
    'archive digest mismatch');
  return JSON.parse(raw.toString('utf8'));
}

export function verifyCareerReadback(body, raceId, horseNumber) {
  assert.equal(body.ok, true);
  let detail=body.detail;
  assert.equal(detail?.id, raceId, 'response race identity mismatch');
  if (detail.arvexqFullPayload) {
    assert.equal(detail.arvexqFullPayload.version, 'arvexq-full-payload-v1');
    detail=restore(detail.arvexqFullPayload, 'gzipBase64', 100000000);
    assert.equal(detail?.id, raceId, 'restored race identity mismatch');
  }
  const horse=detail.horses?.find(h=>Number(h.horseNumber)===horseNumber);
  assert.ok(horse, 'target horse missing from saved race detail');
  const archive=horse.careerArchive;
  assert.ok(archive && typeof archive.payload==='string', 'career archive missing');
  assert.ok(['arvexq-career-gzip-json-v1','arvexq-career-gzip-json-v2'].includes(archive.encoding));
  assert.equal(archive.priorRaceDate, detail.date);
  const runs=restore(archive, 'payload', 15000000);
  assert.ok(Array.isArray(runs));
  const count=archive.includesRecent===true ? archive.storedRunCount : archive.olderRunCount;
  assert.equal(runs.length, Number(count), 'archive run count mismatch');
  return {raceId, horseNumber, storedRuns:runs.length, sha256:archive.sha256,
    restoredFullPayload:Boolean(body.detail.arvexqFullPayload)};
}

if (process.argv[1] && import.meta.url===pathToFileURL(process.argv[1]).href) {
  const raceId=process.argv[2], horseNumber=Number(process.argv[3]);
  assert.ok(raceId && Number.isInteger(horseNumber) && horseNumber>0, 'race and horse number required');
  const url='https://kraiz-api.4b89h4fydd.workers.dev/api/race/'+encodeURIComponent(raceId)+'?archive-check='+Date.now();
  const response=await fetch(url,{signal:AbortSignal.timeout(20000),headers:{'Cache-Control':'no-cache'}});
  assert.equal(response.status,200,'race API returned '+response.status);
  console.log('PRODUCTION_CAREER_ARCHIVE_OK',JSON.stringify(verifyCareerReadback(await response.json(),raceId,horseNumber)));
}
