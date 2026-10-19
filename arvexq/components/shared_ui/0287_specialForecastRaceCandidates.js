function specialForecastRaceCandidates(){
  // Selection membership is frozen once; live results and names do not add races.
  return (state.races||[]).filter(function(r){
    var m=morningPickOf(r);
    return !!(r&&r.id&&m&&m.special===true)
  }).slice().sort(raceChronologicalCompare)
}
