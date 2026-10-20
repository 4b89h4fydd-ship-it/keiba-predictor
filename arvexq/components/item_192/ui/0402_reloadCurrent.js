function reloadCurrent(){
  if(state.race&&state.race.id){
    openRace(state.race.id,true,true,true);return
  }
  if(state.raceLoading){openRace(state.raceLoading,true,true,true);return}

  try{localStorage.removeItem(cacheKey(state.date,state.circuit))}catch(e){}
  state.races=[];
  load(true)
}
