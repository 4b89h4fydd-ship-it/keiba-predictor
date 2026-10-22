'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),zlib=require('node:zlib'),crypto=require('node:crypto');
const w={};
for(const name of ['frozen_ticket_evidence','saved_ticket_receipt'])new Function('window',fs.readFileSync('arvexq/ui/static/morning/'+name+'.js','utf8'))(w);
const manifest=JSON.parse(fs.readFileSync('arvexq/ui/static/saved-snapshots/2026-10-10.json'));
for(const [id,kind,combos] of [['nar-2026-10-10-高知-01','馬単',[[5,8]]],['nar-2026-10-10-高知-05','馬連',[[1,5],[3,5]]]]){
 const ref=manifest.races[id],envelope=JSON.parse(fs.readFileSync('arvexq/ui/static/saved-snapshots/'+ref.file));
 const raw=zlib.gunzipSync(Buffer.from(envelope.gzipBase64,'base64'));
 assert.equal(crypto.createHash('sha256').update(raw).digest('hex'),ref.sha256);
 const r={...JSON.parse(raw),_savedSnapshotFallback:true,_savedSnapshotSHA:ref.sha256};
 const before=JSON.stringify(r),selection={selected:true,primaryType:'勝ち馬明確型',ticketKinds:[kind]};
 const e=w.ARVEXQSavedTicketReceipt.recover(r,selection);
 assert(e&&w.ARVEXQMorningEvidence.verify(r,e),'existing real pre-off original must recover');
 assert.deepEqual(e.items[0].combos,combos);assert.equal(e.fixedAt,r.preRaceBet.fixedAt);
 assert.equal(e.axisHorseNumber,5);assert.equal(e.origin,'saved-preoff');
 assert.equal(JSON.stringify(r),before,'never edit raw prediction or ticket');
 assert.match(w.ARVEXQMorningEvidence.sealedPlan(r,e).reason,/発走前保存/);
 assert.equal(w.ARVEXQSavedTicketReceipt.recover({...r,preRaceBet:{...r.preRaceBet,version:'unverified'}},selection),null);
 assert.equal(w.ARVEXQSavedTicketReceipt.recover({...r,preRaceBet:{...r.preRaceBet,fixedAt:r.date+'T23:59:00+09:00'}},selection),null);
 assert.equal(w.ARVEXQSavedTicketReceipt.recover({...r,preRaceBet:{...r.preRaceBet,axisNo:8}},selection),null);
 assert.equal(w.ARVEXQSavedTicketReceipt.recover(r,{...selection,ticketKinds:['3連単']}),null);
}
// A timestamp on a FAILED capture is not an immutable bet. The very same
// verifier runs in both the browser and the server-side JS capture bridge.
const app=fs.readFileSync('arvexq/ui/static/app.js','utf8');
const from=app.indexOf('function verifiedSavedAiBet('),to=app.indexOf('function frozenAiBetForRace(',from);
assert.ok(from>=0&&to>from);
// Execute the actual public entrypoint through its existing box adapter.
// In Stage 3 the unchanged implementation is stored under a private name.
const privateName='function _arvexq_original_verifiedSavedAiBet(';
const privateFrom=app.indexOf(privateName);
let verify;
if(privateFrom>=0){
 const privateTo=app.indexOf('\nfunction ',privateFrom+privateName.length);
 assert(privateTo>privateFrom,'missing preserved original boundary');
 assert.match(app.slice(from,to),/_arvexq_box_147_call\(_arvexq_original_verifiedSavedAiBet,this,arguments\)/);
 const route=fs.readFileSync('arvexq/components/item_147/routes.js','utf8');
 assert.match(route,/function _arvexq_box_147_call\(/);
 verify=new Function(route+'\n'+app.slice(privateFrom,privateTo)+'\n'+app.slice(from,to)+';return verifiedSavedAiBet;')();
}else{
 verify=new Function(app.slice(from,to)+';return verifiedSavedAiBet;')();
}
const race={id:'nar-2026-10-12-高知-04',date:'2026-10-12',startTime:'18:00'};
const valid={raceId:race.id,raceDate:race.date,fixedAt:'2026-10-12T17:35:00+09:00',
 decision:'通常買い',items:[{kind:'馬連',combos:[[1,2]]}]};
assert.deepEqual(verify(race,valid),valid,'genuine original must survive');
assert.equal(verify(race,{...valid,captureStatus:'failed',decision:'未取得',items:[]}),null);
assert.equal(verify(race,{...valid,captureStatus:'engine-missing',decision:'見送り',items:[]}),null);
assert.equal(verify(race,{...valid,decision:'データ不足',items:[]}),null);
assert.equal(verify(race,{...valid,betInputGate:{ready:false},items:[]}),null);
assert.equal(verify(race,{...valid,fixedAt:'2026-10-12T18:01:00+09:00'}),null);
console.log('SAVED_PREOFF_TICKETS_EXACT_COMBINATIONS_TIMESTAMPS_MARKS_OLDER_ORIGINALS_PASS');
