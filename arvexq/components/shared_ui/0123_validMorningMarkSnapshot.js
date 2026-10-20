function validMorningMarkSnapshot(r){
  var snap=r&&r.morningMarkSnapshot;
  // D1 can lose its prediction row while the original static morning receipt
  // survives. A verified dated receipt is the only alternative evidence.
  if((!snap||!Array.isArray(snap.horses))&&r){
    var evidence=r.morningTicketEvidence,
        source=(typeof window!=='undefined'&&window.ARVEXQMorningEvidence)||null;
    if(source&&source.verify(r,evidence)){
      snap={version:'arvexq-morning-marks-v1',
        raceId:String(r.id),raceDate:String(r.date),
        fixedAt:evidence.fixedAt,source:'static-original-ticket-evidence',
        horses:evidence.marks};
    }
  }
  if(!r||!snap||snap.version!=='arvexq-morning-marks-v1'||
      String(snap.raceId||'')!==String(r.id)||String(snap.raceDate||'')!==String(r.date)||
      !Array.isArray(snap.horses)||snap.horses.length<3)return null;
  var post=Date.parse(String(r.date||'')+'T'+String(r.startTime||r.scheduledStartTime||'').slice(0,5)+':00+09:00'),
      fixed=Date.parse(String(snap.fixedAt||''));
  return isFinite(post)&&isFinite(fixed)&&fixed<post?snap:null
}
