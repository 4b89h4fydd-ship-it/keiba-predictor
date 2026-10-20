function markRelevantInputSignature(r){
  if(!r)return'';
  var horses=(r.horses||[]).map(function(h){
    var x=Object.assign({},h);
    ['winOdds','popularity','oddsForecast','oddsSource','oddsUpdatedAt','marketUpdatedAt'].forEach(function(k){delete x[k]});
    return x;
  });
  return JSON.stringify([r.date,r.startTime,r.distance,r.surface,r.weather,r.condition,
    r.fieldSize,r.markEngineVersion,r.preRacePrediction, horses]);
}
