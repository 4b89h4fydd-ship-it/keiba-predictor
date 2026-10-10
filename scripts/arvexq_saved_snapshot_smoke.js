const assert=require('node:assert/strict'),fs=require('node:fs'),zlib=require('node:zlib'),crypto=require('node:crypto');
const root={};new Function('window',fs.readFileSync('arvexq/ui/static/research/saved_snapshot.js','utf8'))(root);
const d={id:'race1',date:'2026-10-10',horses:[{horseNumber:1,name:'甲'},{horseNumber:2,name:'乙'}],
  preRaceBet:{fixedAt:'2026-10-09T22:00:00Z',items:[{kind:'ワイド',combos:[[1,2]]}]},
  morningMarkSnapshot:{horses:[{horseNumber:1,mark:'◎'}]},allCareer:{data:'preserve'}};
const raw=Buffer.from(JSON.stringify(d)),hash=crypto.createHash('sha256').update(raw).digest('hex');
const e={version:'arvexq-saved-snapshot-v1',bytes:raw.length,sha256:hash,gzipBase64:zlib.gzipSync(raw).toString('base64')};
function manifest(day,id){return {version:'arvexq-saved-snapshots-v1',date:day,races:{[id]:{file:hash+'.json',sha256:hash,bytes:raw.length}}}}
(async()=>{
  const result=await root.ARVEXQSavedSnapshot.available(d.date,d.id,async path=>path.endsWith(hash+'.json')?e:manifest(d.date,d.id));
  assert.equal(result._savedSnapshotFallback,true);
  const pre={...result,preRacePrediction:{raceId:d.id,raceDate:d.date,capturedAtEpoch:1791580000,frozen:false,
    horses:[{horseNumber:1,mark:'◎'},{horseNumber:2,mark:'○'}]}};
  pre.startTime='10:00';
  pre._savedPreoffOriginal=pre.preRacePrediction;
  pre._savedOriginalField=pre.horses;
  const before=JSON.stringify(pre.preRacePrediction);
  assert.equal(root.ARVEXQSavedSnapshot.marks(pre).horses[0].mark,'◎');
  assert.equal(JSON.stringify(pre.preRacePrediction),before,'must not change frozen flag or original');
  assert.equal(root.ARVEXQSavedSnapshot.marks({...pre,_savedSnapshotFallback:false}),null);
  assert.equal(root.ARVEXQSavedSnapshot.marks({...pre,_savedPreoffOriginal:{...pre.preRacePrediction,capturedAtEpoch:1791660000}}),null,'post-off original rejected');
  assert.equal(root.ARVEXQSavedSnapshot.marks({...pre,_savedPreoffOriginal:{...pre.preRacePrediction,horses:[{horseNumber:1,mark:'◎'},{horseNumber:1,mark:'○'}]}}),null);
  const withdrawn={...pre,horses:[...pre.horses,{horseNumber:3,name:'取消馬',scratched:true}]};
  withdrawn._savedOriginalField=withdrawn.horses;
  assert.ok(root.ARVEXQSavedSnapshot.marks(withdrawn),'withdrawn runner omitted in original is valid');
  assert.equal(root.ARVEXQSavedSnapshot.marks({...withdrawn,_savedOriginalField:[...pre.horses,{horseNumber:3,name:'未分析馬'}],horses:[...pre.horses,{horseNumber:3,name:'未分析馬'}]}),null,'active runner without original must reject');
  delete result._savedSnapshotFallback;delete result._savedPreoffOriginal;delete result._savedOriginalField;assert.deepEqual(result,d);
  const corrupt=await root.ARVEXQSavedSnapshot.available('2026-10-11','race2',async path=>path.endsWith(hash+'.json')?{...e,gzipBase64:zlib.gzipSync(Buffer.from(' '.repeat(raw.length))).toString('base64')}:manifest('2026-10-11','race2'));
  assert.equal(corrupt,null,'hash mismatch must never display');
  assert.equal(await root.ARVEXQSavedSnapshot.available('2026-10-12','race3',async path=>path.endsWith(hash+'.json')?e:manifest('2026-10-12','race3')),null,'wrong race/date must never display');
  console.log('LOSSLESS_SNAPSHOT_BROWSER_RESTORE_HASH_IDENTITY_PASS');
})().catch(e=>{console.error(e);process.exitCode=1});
