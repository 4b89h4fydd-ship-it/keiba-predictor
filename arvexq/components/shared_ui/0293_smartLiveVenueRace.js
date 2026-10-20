function smartLiveVenueRace(rows,now){
  var active=(rows||[]).filter(function(r){return !isFinal(r)&&r.startTime});
  if(!active.length)return null;
  var running=active.filter(function(r){var d=mins(r.startTime)-now;return d<0&&d>=-25})
    .sort(function(a,b){return mins(b.startTime)-mins(a.startTime)});
  if(running.length)return running[0];
  var future=active.filter(function(r){return mins(r.startTime)>=now})
    .sort(function(a,b){return mins(a.startTime)-mins(b.startTime)});
  return future.length?future[0]:null
}
