function morningPickOf(r){
  if(!r)return null;
  var v=r.volatility&&r.volatility.morningPicks,
      e=r.environmentMeta&&r.environmentMeta.morningPicks,
      m=v&&v.version==='v1'&&v.fixedAt?v:(e&&e.version==='v1'&&e.fixedAt?e:null);
  if(m)return m;
  if(r.morningPickVersion==='v1'&&r.morningPickFixedAt)return {
    version:'v1',fixedAt:String(r.morningPickFixedAt),
    selected:r.morningSelected===true,selectedScore:n(r.morningSelectedScore,0),
    special:r.morningSpecial===true,scope:n(r.morningPickScope,0),assessed:r.morningAssessed!==false,
    selectionModelVersion:String(r.morningSelectionModelVersion||''),
     primaryType:String(r.morningPrimaryType||''),types:Array.isArray(r.morningSelectedTypes)?r.morningSelectedTypes.slice():[],
     selectionReason:String(r.morningSelectionReason||''),
     ticketKinds:Array.isArray(r.morningTicketKinds)?r.morningTicketKinds.slice():[],
     ticketEvidence:r.morningTicketEvidence||null
  };
  return null
}
