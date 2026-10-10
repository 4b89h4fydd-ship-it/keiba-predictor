'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),zlib=require('node:zlib'),crypto=require('node:crypto');
const w={};
for(const name of ['frozen_ticket_evidence','saved_ticket_receipt'])new Function('window',fs.readFileSync('arvexq/ui/static/morning/'+name+'.js','utf8'))(w);
const manifest=JSON.parse(fs.readFileSync('arvexq/ui/static/saved-snapshots/2026-10-10.json'));
for(const [id,kind,combos] of [['nar-2026-10-10-高知-01','馬単',[[5,8]]],['nar-2026-10-10-高知-05','馬連',[[1,5],[3,5]]]]){
 const ref=manifest.races[id],envelope=JSON.parse(fs.readFileSync('arvexq/ui/static/saved-snapshots/'+ref.file));
 const raw=zlib.gunzipSync(Buffer.from(envelope.gzipBase64,'base64'));
 assert.equal(crypto.createHash('sha256').update(raw).digest('hex'),ref.sha256);
 assert(fs.existsSync('arvexq/ui/static/saved-snapshots/'+ref.previousSnapshot.file),'older original is preserved');
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
console.log('SAVED_PREOFF_TICKETS_EXACT_COMBINATIONS_TIMESTAMPS_MARKS_OLDER_ORIGINALS_PASS');
