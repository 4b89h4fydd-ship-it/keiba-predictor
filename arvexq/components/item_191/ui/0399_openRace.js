function openRace(id,keepStack,skipHistory,preservePanel){
  if(!id)return;
  if(previousAiStats.loading){
    ++previousAiStatsJob;
    previousAiStats.loading=false;
    previousAiStats.done=false;
  }
  if(state.oddsTimer){clearTimeout(state.oddsTimer);state.oddsTimer=null}
  state.oddsBusy=false;
  if(state.environmentTimer){clearTimeout(state.environmentTimer);state.environmentTimer=null}
  // v235: when moving with the race < / > controls, keep the currently selected panel.
  // Normal venue/top selections still open the racecard first.
  var preservedPanel=preservePanel?(state.openPanel||'entry'):null;
  state.openPanel=preservedPanel||'entry';
  var seq=++state.detailSeq;
  if(!keepStack){state.raceStack=[];state.raceReturnPicker=state.picker}
  state.horseModalNo=null;state.detailHorseNo=null;state.subPage=null;state.subPageReturnPanel=null;
  if(state.historyTimer){clearTimeout(state.historyTimer);state.historyTimer=null}
  state.error=null;
  state.pred=null;
  state.picker=false;
  state.scenarioCode=null;
  state.paceStage=0;

  var row=(state.races||[]).find(function(x){return String(x&&x.id||'')===String(id)}),cached=instantTrackDetails[String(id)]||loadDetailCache(id,true);
  var initial=mergeRaceReflection(normalizeDetailSummary(row,id),cached,null,null);
  initial=normalizeDetailSummary(initial,id);
  var st=detailState(id);st.error='';updateDetailSections(id,initial,false);
  state.raceLoading=null;
  state.race=applySummaryEnvironment(initial);
  render();
  // Start the verified local roster without waiting for the slower D1/full-history path.
  hydrateStaticRacecardFirst(id,seq,initial);
  if(entryDataAvailable(initial))fetchSelectedRaceOdds(id,seq);
  // One authoritative detail request. The dated immutable factual card is
  // painted immediately above; retired parallel racecard/snapshot fetches no
  // longer race to replace a healthy D1 detail.
  fetchEdgeRace(id,true,2).then(function(body){
    if(seq!==state.detailSeq||!state.race||String(state.race.id)!==String(id))return;
    if(body){
      state.race=applySummaryEnvironment(mergeRaceReflection(state.race,body,null,null));
      instantTrackDetails[String(id)]=state.race;saveDetailCache(id,state.race);
    }
    if(entryDataAvailable(state.race)){
      updateDetailSections(id,state.race,true);render();
      if(!entryDataAvailable(initial))fetchSelectedRaceOdds(id,seq);
      return;
    }
    // An explicit 0-horse official response is different from a failed fetch.
    // Keep its confirmed-empty state instead of allowing a failed secondary
    // racecard request to downgrade it to "loading" forever.
    if(body&&Array.isArray(body.horses)&&body.horses.length===0&&
       body.fieldSize!=null&&Number(body.fieldSize)===0){
      updateDetailSections(id,state.race,true);render();
      return;
    }
    // Only when D1 and the vetted dated archive could not supply any runners,
    // ask the narrow racecard endpoint once. It is not a second live source.
    return fetchRacecardOnly(id).then(function(card){
      if(seq!==state.detailSeq||!state.race||String(state.race.id)!==String(id))return;
      if(card&&entryDataAvailable(card)){
        state.race=applySummaryEnvironment(mergeRaceReflection(state.race,card,null,row));
        instantTrackDetails[String(id)]=state.race;saveDetailCache(id,state.race);
        st.error='';
        traceRaceDetail(id,'racecard-last-resort',{horses:(card.horses||[]).length});
        fetchSelectedRaceOdds(id,seq);
      }
      updateDetailSections(id,state.race,!!card);render();
    });
  }).catch(function(error){
    if(seq!==state.detailSeq)return;
    st.error=String(error&&error.message||error);
    updateDetailSections(id,state.race,false);render()
  })
}

