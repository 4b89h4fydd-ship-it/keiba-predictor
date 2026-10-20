function applyMorningArchive(rows){
  var archive=state.morningArchive;
  if(!archive||archive.date!==state.date||!Array.isArray(archive.races))return rows;
  var picks={};
  archive.races.forEach(function(x){if(x&&x.id)picks[String(x.id)]=x});
  (rows||[]).forEach(function(r){
    if(!r||!r.id)return;
    var frozen=picks[String(r.id)];
    if(!frozen)return;
    var m={
      version:'v1',fixedAt:archive.fixedAt,scope:archive.scope,
      selected:frozen.selected===true,selectedScore:n(frozen.selectedScore,0),
      special:frozen.special===true,assessed:frozen.assessed!==false,
       primaryType:String(frozen.primaryType||''),types:Array.isArray(frozen.types)?frozen.types.slice():[],
       selectionReason:String(frozen.selectionReason||''),
       ticketKinds:Array.isArray(frozen.ticketKinds)?frozen.ticketKinds.slice():[],
       ticketEvidence:frozen.ticketEvidence||null
    };
    if(!m.ticketEvidence&&window.ARVEXQSavedTicketReceipt)m.ticketEvidence=window.ARVEXQSavedTicketReceipt.recover(r,m);
    r.morningPickVersion='v1';
    r.morningPickFixedAt=archive.fixedAt;
    r.morningPickScope=archive.scope;
    r.morningSelected=m.selected;r.morningSelectedScore=m.selectedScore;
    r.morningSpecial=m.special;r.morningAssessed=m.assessed;
     r.morningPrimaryType=m.primaryType;r.morningSelectedTypes=m.types.slice();
     r.morningSelectionReason=m.selectionReason;r.morningTicketKinds=m.ticketKinds.slice();
     r.morningTicketEvidence=m.ticketEvidence;
     if(m.ticketEvidence&&window.ARVEXQMorningEvidence&&window.ARVEXQMorningEvidence.verify(r,m.ticketEvidence)){
       var d=instantTrackDetails[String(r.id)];
       if(d&&String(d.date||'')===String(r.date))d.morningTicketEvidence=m.ticketEvidence;
     }
    r.volatility=Object.assign({},r.volatility||{},{morningPicks:m});
    r.environmentMeta=Object.assign({},r.environmentMeta||{},{morningPicks:m})
  });
  return rows
}
