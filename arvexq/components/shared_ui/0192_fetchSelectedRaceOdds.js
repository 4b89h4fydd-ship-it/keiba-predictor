function fetchSelectedRaceOdds(id,seq,force){
  return window.ARVEXQLiveOdds.fetch(id,edgeFetchJson,force).then(function(body){
    if(seq!==state.detailSeq||!state.race||String(state.race.id)!==String(id))return false;
    var changed=mergeOddsPayload(body);
    updateDetailSections(id,state.race,false);
    if(changed){saveDetailCache(id,state.race);render()}
    else render();
    return changed
  }).catch(function(error){
    traceRaceDetail(id,'odds-failed',{message:String(error&&error.message||error)});
    if(seq===state.detailSeq&&state.race&&String(state.race.id)===String(id)){
      if(!raceHasOdds(state.race))detailState(id).odds='error';
      var status=document.getElementById('odds-status');
      if(status)status.textContent='更新失敗｜'+window.ARVEXQLiveOdds.status(state.race)
    }
    return false
  })
}
