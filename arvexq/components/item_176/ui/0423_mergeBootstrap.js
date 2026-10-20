function mergeBootstrap(body){
  var rows=(body&&body.races)||[],details=(body&&body.details)||[],pvol={};
  state.bootstrapReady=!!(body&&body.complete===true);
  details.forEach(function(d){
    if(!d||!d.id)return;
    instantTrackDetails[String(d.id)]=d;
    saveDetailCache(d.id,d);
    if(d.volatility)pvol[String(d.id)]=d.volatility
  });
  rows.forEach(function(r){
    var d=instantTrackDetails[String(r.id)];
    if(d){
      if(d.volatility){
        var morning=morningPickOf(r);
        r.volatility=Object.assign({},d.volatility);
        if(morning)r.volatility.morningPicks=morning
      }
      if(d.weather&&d.weather!=='不明')r.weather=d.weather;
      if(d.condition&&d.condition!=='不明')r.condition=d.condition;
      if(d.oddsUpdatedAt)r.oddsUpdatedAt=d.oddsUpdatedAt
    }else if(pvol[String(r.id)]){
      r.volatility=pvol[String(r.id)]
    }
  });
  return applyMorningArchive(rows)
}


