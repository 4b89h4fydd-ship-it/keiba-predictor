function persistRaceSummaryCache(){
  try{
    var hasCentral=state.races.some(function(x){return x.circuit==='中央'}),
        hasLocal=state.races.some(function(x){return x.circuit==='地方'});
    if(hasCentral&&hasLocal)saveRaceCache(state.date,'__ALL__',state.races);
    else saveRaceCache(state.date,state.circuit,state.races)
  }catch(e){}
}
