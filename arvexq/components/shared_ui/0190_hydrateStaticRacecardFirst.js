function hydrateStaticRacecardFirst(id,seq,summary){
  var loader=window.ARVEXQStaticRacecard;
  if(!loader||typeof loader.available!=='function')return Promise.resolve(false);
  var date=String((summary||{}).date||state.date||'');
  if(!/^20\d{2}-\d{2}-\d{2}$/.test(date))return Promise.resolve(false);
  return loader.available(date,id,function(path){return edgeFetchJson(path,6500)}).then(function(card){
    if(seq!==state.detailSeq||!card||String(card.id)!==String(id)||
       !state.race||String(state.race.id)!==String(id))return false;
    // A complete API or verified full snapshot always takes precedence.
    if(entryDataAvailable(state.race)&&(state.race.horses||[]).length>=card.horses.length)return false;
    state.race=applySummaryEnvironment(mergeRaceReflection(state.race,card,null,null));
    state.race._entryOnly=true;state.race._staticRacecardFallback=true;
    instantTrackDetails[String(id)]=state.race;saveDetailCache(id,state.race);
    updateDetailSections(id,state.race,true);
    traceRaceDetail(id,'racecard-static-first',{date:date,horses:card.horses.length});
    render();
    return true;
  }).catch(function(error){
    traceRaceDetail(id,'racecard-static-first-failed',{message:String(error&&error.message||error)});
    return false;
  });
}
