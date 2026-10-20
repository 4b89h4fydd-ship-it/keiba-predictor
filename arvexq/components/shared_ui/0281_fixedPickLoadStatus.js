function fixedPickLoadStatus(circuit){
  var rows=(state.races||[]).filter(function(r){return r&&r.id&&String(r.circuit||'')===String(circuit)}),loaded=0;
  rows.forEach(function(r){var d=instantTrackDetails[String(r.id)]||loadDetailCache(r.id);if(d&&raceDisplayCoreReady(d,r||d))loaded++});
  return{expected:rows.length,loaded:loaded,complete:rows.length?loaded>=rows.length:selectedRaceLoadStatus().complete,partial:loaded>0}
}
