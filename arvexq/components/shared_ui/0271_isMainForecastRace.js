function isMainForecastRace(r){
  if(!r||!r.id)return false;
  var circuit=String(r.circuit||''),track=String(r.track||''),rows=(state.races||[]).filter(function(z){
    if(!z||!z.id||String(z.track||'')!==track)return false;
    return !circuit||!z.circuit||String(z.circuit||'')===circuit
  }),main=mainRaceForTrack(rows);
  return !!(main&&String(main.id)===String(r.id))
}
