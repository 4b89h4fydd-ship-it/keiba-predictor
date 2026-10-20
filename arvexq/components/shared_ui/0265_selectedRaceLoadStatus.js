function selectedRaceLoadStatus(){
  var expected=n(selectedRacePreload.expectedCount,0)||(state.races||[]).filter(function(r){return r&&r.id}).length,loaded=n(selectedRacePreload.loadedCount,0);
  return{expected:expected,loaded:loaded,complete:!!selectedRacePreload.fullLoaded,loading:!!selectedRacePreload.fullLoading,error:selectedRacePreload.lastError||''}
}
