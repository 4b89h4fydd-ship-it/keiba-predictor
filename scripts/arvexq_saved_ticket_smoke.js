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
// A timestamp on a FAILED capture is not an immutable bet. This gate used
// to be exercised through a copy embedded in the old app.js
// (verifiedSavedAiBet), but that app is gone: the UI was rebuilt as an
// entry-table-only app with no betting logic, and the capture bridge
// that minted new receipts (scripts/arvexq_capture_prerace_bet.js) is
// retired. The gate's surviving home is ARVEXQMorningEvidence.capture /
// verify — the very functions recover() above runs against the stored
// originals — so the same cases are asserted against them directly.
const ev=w.ARVEXQMorningEvidence;
const race={id:'nar-2026-10-12-高知-04',date:'2026-10-12',startTime:'18:00'};
const prediction={rows:[
 {horse:{horseNumber:1},predMark:'◎',singleWinSuitable:true},
 {horse:{horseNumber:2},predMark:'○',singleWinSuitable:false},
 {horse:{horseNumber:3},predMark:'▲',singleWinSuitable:false},
 {horse:{horseNumber:4},predMark:'',singleWinSuitable:false},
 {horse:{horseNumber:5},predMark:'',singleWinSuitable:false}]};
const plan={decision:'通常買い',betInputGate:{ready:true},engineVersion:'smoke',
 items:[{level:'本線',kind:'馬連',combos:[[1,2]],reason:'smoke'}]};
const sel={selected:true,primaryType:'勝ち馬明確型',ticketKinds:['馬連']};
const minted=ev.capture(race,prediction,plan,sel);
assert(minted&&minted.axisHorseNumber===1,'genuine original must mint evidence');
const sealed={...minted,fixedAt:'2026-10-12T17:35:00+09:00'};
assert.equal(ev.verify(race,sealed),true,'genuine original must survive');
assert(ev.sealedPlan(race,sealed),'genuine original must seal');
assert.equal(ev.capture(race,prediction,{...plan,decision:'未取得'},sel),null);
assert.equal(ev.capture(race,prediction,{...plan,decision:'見送り'},sel),null);
assert.equal(ev.capture(race,prediction,{...plan,decision:'データ不足'},sel),null);
assert.equal(ev.capture(race,prediction,{...plan,betInputGate:{ready:false}},sel),null);
assert.equal(ev.verify(race,{...sealed,fixedAt:'2026-10-12T18:01:00+09:00'}),false);
console.log('SAVED_PREOFF_TICKETS_EXACT_COMBINATIONS_TIMESTAMPS_MARKS_OLDER_ORIGINALS_PASS');
