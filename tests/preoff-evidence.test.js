import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { gzipSync } from 'node:zlib';
import { handlePreoffCapture } from '../preoff-evidence.js';

function stable(v) {
  if (Array.isArray(v)) return '[' + v.map(stable).join(',') + ']';
  if (v && typeof v === 'object') return '{' + Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+stable(v[k])).join(',') + '}';
  return JSON.stringify(v);
}
const hash = v => createHash('sha256').update(stable(v)).digest('hex');
const clock = 1790000000;
const token = 'test-capture-token-more-than-24-characters';

function fixture() {
  const snapshot = {raceId:'nar-2026-09-21-園田-01',date:'2026-09-21',circuit:'地方',
    horseCount:3,rows:[1,2,3].map(n=>({horseNumber:n,features:{'static::age':n+3}}))};
  snapshot.featureHash = hash(snapshot);
  const receipt = {version:'arvexq-preoff-raw-evidence-v1',source:'preoff-acquisition-log',
    attestedPreOff:true,raceId:snapshot.raceId,featureHash:snapshot.featureHash,
    capturedAtEpoch:clock - 10,postAtEpoch:clock + 600,activeHorseNumbers:[1,2,3]};
  // Test chooses ISO date from actual JST timestamp, independent of displayed race naming.
  snapshot.date = new Date((receipt.postAtEpoch+9*3600)*1000).toISOString().slice(0,10);
  snapshot.featureHash = hash(Object.fromEntries(Object.entries(snapshot).filter(([k])=>k!=='featureHash')));
  receipt.featureHash = snapshot.featureHash;
  receipt.receiptHash = hash(receipt);
  return {snapshot,receipt};
}
function request(body,{auth=true,method='POST'}={}) {
  return new Request('https://example.com/api/research/preoff-evidence',{method,
    headers:{...(auth?{authorization:'Bearer '+token}:{}),'content-type':'application/json'},
    ...(method==='POST'?{body:JSON.stringify({
      ...body,
      snapshotCoreCanonical:body.snapshotCoreCanonical ?? stable(Object.fromEntries(Object.entries(body.snapshot).filter(([k])=>k!=='featureHash'))),
      receiptCoreCanonical:body.receiptCoreCanonical ?? stable(Object.fromEntries(Object.entries(body.receipt).filter(([k])=>k!=='receiptHash')))
    })}:{})});
}
function db() {
  const rows=new Map();
  return {rows,prepare(sql){
    const state={values:[],bind(...vals){this.values=vals;return this},
      async run(){const v=this.values;if(rows.has(v[0]))return {meta:{changes:0}};
        rows.set(v[0],v);return {meta:{changes:1}}},
      async first(){let v=rows.get(this.values[0]);return v?{feature_hash:v[2],receipt_hash:v[3],
        snapshot_json:v[4],receipt_json:v[5]}:null}};
    return state;
  }};
}
const env = DB=>({DB,FORECAST_CAPTURE_TOKEN:token});
const run=(b,d,opts)=>handlePreoffCapture(request(b,opts),env(d),{now:()=>clock});

test('new validated capture inserts once and identical replay is idempotent',async()=>{
  const d=db(),b=fixture();
  let r=await run(b,d);assert.equal(r.status,201);const id=(await r.json()).captureId;
  r=await run(b,d);assert.equal(r.status,200);assert.equal((await r.json()).captureId,id);
  assert.equal(d.rows.size,1);
});
test('rejects missing authorization and late capture',async()=>{
  const d=db(),b=fixture();
  assert.equal((await run(b,d,{auth:false})).status,401);
  b.receipt.capturedAtEpoch=clock-600;b.receipt.receiptHash=hash(Object.fromEntries(Object.entries(b.receipt).filter(([k])=>k!=='receiptHash')));
  assert.equal((await run(b,d)).status,422);
  assert.equal(d.rows.size,0);
});
test('rejects changed feature data and unverified runner identity',async()=>{
  const d=db(),b=fixture();
  b.snapshot.rows[0].features['static::age']=999;
  assert.equal((await run(b,d)).status,422);
  const other=fixture();
  other.receipt.activeHorseNumbers=[1,2,4];
  other.receipt.receiptHash=hash(Object.fromEntries(Object.entries(other.receipt).filter(([k])=>k!=='receiptHash')));
  assert.equal((await run(other,d)).status,422);
  assert.equal(d.rows.size,0);
});
test('fails closed when D1 migration is missing',async()=>{
  const unavailable={prepare(){return {bind(){return this},async run(){throw new Error('no such table: forecast_preoff_evidence')}}}};
  const r=await run(fixture(),unavailable);assert.equal(r.status,503);
});

test('Python float token 55.0 hashes exactly, not JavaScript 55',async()=>{
  const d=db(), b=fixture();
  b.snapshot.rows[0].features['static::age']=55;
  const core=stable(Object.fromEntries(Object.entries(b.snapshot).filter(([k])=>k!=='featureHash')));
  b.snapshotCoreCanonical=core.replace('"static::age":55','"static::age":55.0');
  b.snapshot.featureHash=createHash('sha256').update(b.snapshotCoreCanonical).digest('hex');
  b.receipt.featureHash=b.snapshot.featureHash;
  b.receiptCoreCanonical=stable(Object.fromEntries(Object.entries(b.receipt).filter(([k])=>k!=='receiptHash')));
  b.receipt.receiptHash=hash(Object.fromEntries(Object.entries(b.receipt).filter(([k])=>k!=='receiptHash')));
  let r=await run(b,d);
  assert.equal(r.status,201);
  assert.equal(d.rows.size,1);
});

test('large lossless compressed envelope survives validation and duplicate replay',async()=>{
  const d=db(), b=fixture();
  for (const row of b.snapshot.rows) {
    for (let i=0;i<16000;i++) row.features['history::all::w5::feature_'+i]=i*.5;
  }
  b.snapshot.featureHash=hash(Object.fromEntries(Object.entries(b.snapshot).filter(([k])=>k!=='featureHash')));
  b.receipt.featureHash=b.snapshot.featureHash;
  b.receipt.receiptHash=hash(Object.fromEntries(Object.entries(b.receipt).filter(([k])=>k!=='receiptHash')));
  const full={...b,
    snapshotCoreCanonical:stable(Object.fromEntries(Object.entries(b.snapshot).filter(([k])=>k!=='featureHash'))),
    receiptCoreCanonical:stable(Object.fromEntries(Object.entries(b.receipt).filter(([k])=>k!=='receiptHash')))
  };
  const raw=JSON.stringify(full);
  assert.ok(Buffer.byteLength(raw)>950000);
  const compressed=gzipSync(Buffer.from(raw),{mtime:0}).toString('base64');
  const makeRequest=()=>new Request('https://example.com/api/research/preoff-evidence',{
    method:'POST',headers:{authorization:'Bearer '+token,'content-type':'application/json'},
    body:JSON.stringify({encoding:'arvexq-preoff-gzip-json-v1',payload:compressed})
  });
  let response=await handlePreoffCapture(makeRequest(),env(d),{now:()=>clock});
  assert.equal(response.status,201,await response.text());
  response=await handlePreoffCapture(makeRequest(),env(d),{now:()=>clock});
  assert.equal(response.status,200);
  assert.equal(d.rows.size,1);
  const stored=[...d.rows.values()][0][4];
  assert.ok(stored.startsWith('gzip-envelope:'));
  assert.equal(JSON.parse((await import('node:zlib')).gunzipSync(Buffer.from(stored.slice('gzip-envelope:'.length),'base64')).toString()).snapshot.rows.length,3);
});
