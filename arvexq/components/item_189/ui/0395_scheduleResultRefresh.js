function scheduleResultRefresh(){
  var r=state.race;
  if(!r||!r.id||!r.startTime||!/^\d{4}-\d{2}-\d{2}$/.test(String(r.date||''))||
      String(r.date||'')>today()||
      (Date.parse(today()+'T00:00:00+09:00')-Date.parse(String(r.date||'')+'T00:00:00+09:00'))>7*86400000||
      (isFinal(r)&&hasResultData(r)&&((r.result||{}).payouts||[]).length>0)){
    if(state.resultTimer){clearTimeout(state.resultTimer);state.resultTimer=null}
    return;
  }
  var id=String(r.id);
  if(state.resultTimer&&resultPollActiveId===id)return;
  if(state.resultTimer){clearTimeout(state.resultTimer);state.resultTimer=null}
  if(resultPollBusy)return;
  resultPollActiveId=id;
  var delta=mins(r.startTime)-nowMins();
  var wait=delta>3?Math.min(300000,Math.max(30000,(delta-2)*60000)):20000;
  state.resultTimer=setTimeout(function(){
    state.resultTimer=null;
    var seq=state.detailSeq;
    if(!state.race||String(state.race.id)!==id)return;
    resultPollBusy=true;
    fetchEdgeRace(id,true,1).then(function(body){
      if(!body||seq!==state.detailSeq||!state.race||String(state.race.id)!==id)return;
      state.race=applySummaryEnvironment(mergeRaceReflection(state.race,body,null,null));
      instantTrackDetails[id]=state.race;saveDetailCache(id,state.race);
      updateDetailSections(id,state.race,true);
      // Keep the opened tab, historical predictions and tickets unchanged.
      render()
    }).catch(function(error){
      traceRaceDetail(id,'result-poll-failed',{message:String(error&&error.message||error)});
      if(state.race&&String(state.race.id)===id)detailState(id).result='error';
    }).finally(function(){
      resultPollBusy=false;
      scheduleResultRefresh()
    })
  },wait)
}

