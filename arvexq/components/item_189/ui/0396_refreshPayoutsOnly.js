function refreshPayoutsOnly(attempt){
  var r=state.race;
  if(!r||!r.id||state.payoutBusy)return;
  state.payoutBusy=true;
  fetchEdgeRace(r.id,true)
    .then(function(body){
      if(!body||!state.race||String(state.race.id)!==String(r.id))return;
      state.race=applySummaryEnvironment(mergeRaceReflection(state.race,body,null,null));
      saveDetailCache(r.id,state.race)
    })
    .catch(function(error){traceRaceDetail(r.id,'payout-refresh-failed',{message:String(error&&error.message||error)})})
    .finally(function(){state.payoutBusy=false;if(state.race&&String(state.race.id)===String(r.id))render()})
}



