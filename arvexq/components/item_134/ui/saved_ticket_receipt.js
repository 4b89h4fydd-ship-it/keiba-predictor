/* Recover only an existing, hash-verified pre-off bet. Never calculate tickets. */
(function(root){
'use strict';
const originals=new Map(),days=new Map();
async function load(date,fetchJson){
 if(!days.has(date))days.set(date,(async()=>{
  const manifest=await fetchJson('/saved-snapshots/'+date+'.json',6500);
  if(!manifest||manifest.date!==date||!manifest.races)return;
  await Promise.all(Object.entries(manifest.races).filter(([,ref])=>ref.bet===true).map(async([id])=>{
   const r=await root.ARVEXQSavedSnapshot.available(date,id,fetchJson);
   if(r)originals.set(date+'|'+id,r);
  }));
 })().catch(()=>{days.delete(date)}));
 return days.get(date);
}
function recover(r,selection){
 const cached=r&&originals.get(r.date+'|'+r.id);
 if(cached&&!r.preRaceBet)r=cached;
 const module=root.ARVEXQMorningEvidence,q=r&&r.preRacePrediction,b=r&&r.preRaceBet;
 if(!module||!r||!q||q.frozen!==true||!b||
    b.version!=='arvexq-server-exact-js-bet-v1'||
    b.lockPolicy!=='server-js-ticket-v1-no-post-hoc'||b.fixedBeforePost!==true||
    b.captureError||!b.fixedAt||!/^[a-f0-9]{64}$/.test(String(b.jsHash||''))||
    q.raceId!==r.id||q.raceDate!==r.date||!Array.isArray(q.horses))return null;
 const post=Date.parse(r.date+'T'+String(r.scheduledStartTime||r.startTime||'').slice(0,5)+':00+09:00');
 if(!Number.isFinite(post)||!(Number(q.capturedAtEpoch)>0&&Number(q.capturedAtEpoch)*1000<post)||Date.parse(b.fixedAt)>=post)return null;
 const known=new Map((r.horses||[]).map(h=>[h.horseNumber,h]));
 const rows=q.horses.map(h=>({horse:known.get(h.horseNumber),predMark:String(h.mark||''),singleWinSuitable:!!h.singleWinSuitable}));
 if(rows.some(x=>!x.horse))return null;
 const receipt=module.capture(r,{rows},b,selection);
 if(!receipt||receipt.axisHorseNumber!==Number(b.axisNo||0))return null;
 receipt.fixedAt=b.fixedAt;
 receipt.origin='saved-preoff';
 receipt.sourceSnapshotSha256=r._savedSnapshotSHA||'';
 return module.verify(r,receipt)?receipt:null;
}
root.ARVEXQSavedTicketReceipt=Object.freeze({recover,load});
})(window);
