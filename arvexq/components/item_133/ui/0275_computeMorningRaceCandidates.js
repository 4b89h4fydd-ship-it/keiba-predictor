function computeMorningRaceCandidates(circuit){
 if(!window.ARVEXQSelectedRacePipeline)throw Error('morning selector module missing');
 return window.ARVEXQSelectedRacePipeline.select(
  (state.races||[]).filter(function(r){return r&&r.id&&(!circuit||String(r.circuit||'')===String(circuit))}),
  {getDetail:function(r){return instantTrackDetails[String(r.id)]||loadDetailCache(r.id)},
   isFinal:isFinal,isScratch:isScratchHorse,predict:predict,
   evaluateQuality:function(){return {selected:false,failed:["予想未設定"]}},makeTicket:buildAiBetPlan,
   lanes:window.ARVEXQMorningTicketLanes,evidence:window.ARVEXQMorningEvidence,
   cut:eliteSelectedRaceCut,warn:function(){console.warn.apply(console,arguments)}})
}
