function homePickCounts(kind){
  if(kind==='selected')return {
    central:selectedRaceCandidates('中央').length,
    local:selectedRaceCandidates('地方').length
  };
  var rows=specialForecastRaceCandidates();
  return {
    central:rows.filter(function(r){return String(r.circuit||'')==='中央'}).length,
    local:rows.filter(function(r){return String(r.circuit||'')==='地方'}).length
  }
}
