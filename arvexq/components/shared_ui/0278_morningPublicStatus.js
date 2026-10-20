function morningPublicStatus(r){
  var m=morningPickOf(r),mod=window.ARVEXQMorningTicketLanes,
      receipt=window.ARVEXQMorningEvidence;
  var status=mod&&mod.selectionDisplayStatus?mod.selectionDisplayStatus(m,r):'unavailable';
  if(status!=='actionable')return status;
  // A frozen ticket kind without actual horse-number combinations is
  // an unverified historic selection, not a purchasable recommendation.
  if(!receipt||typeof receipt.verify!=='function'||
     !receipt.verify(r,m&&m.ticketEvidence)||!m.ticketEvidence||
     (m.ticketKinds||[]).slice().sort().join('|')!==
       (m.ticketEvidence.ticketKinds||[]).slice().sort().join('|'))
    return 'ticket-original-missing';
  return 'actionable'
}
