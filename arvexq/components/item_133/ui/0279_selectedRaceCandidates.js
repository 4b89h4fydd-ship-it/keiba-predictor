function selectedRaceCandidates(circuit){
  // Published free selections require a frozen ticket-backed type.
  return (state.races||[]).filter(function(r){
    var m=morningPickOf(r);
    return !!(r&&r.id&&m&&morningPublicStatus(r)==='actionable'&&String(m.selectionModelVersion||'')==='arvexq-empirical-ticket-hit-v1'&&
      String(m.primaryType||'')==='的中重視型'&&Array.isArray(m.types)&&m.types.includes('的中重視型')&&
      (!circuit||String(r.circuit||'')===String(circuit)))
  }).map(function(r){
    var m=morningPickOf(r);
    return {race:r,tags:['厳選'],selection:{
      selected:true,score:n(m&&m.selectedScore,0),
      reason:String(m&&m.selectionReason||'朝の事前選定固定'),
       primaryType:String(m&&m.primaryType||''),types:Array.isArray(m&&m.types)?m.types.slice():[],
       fixedAt:String(m&&m.fixedAt||''),
       ticketKinds:Array.isArray(m&&m.ticketKinds)?m.ticketKinds.slice():[],
       noAxis:!!(m&&m.ticketEvidence&&m.ticketEvidence.axisStatus==='no-axis')
    }}
  }).sort(raceChronologicalCompare)
}
