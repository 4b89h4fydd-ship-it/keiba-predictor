function mergeVolatilityPack(rows){
  var changed=false,map={};
  (rows||[]).forEach(function(x){if(x&&x.id)map[String(x.id)]=x.volatility||null});
  state.races.forEach(function(r){
    var v=map[String(r.id)];
    if(v&&JSON.stringify(r.volatility||null)!==JSON.stringify(v)){r.volatility=v;changed=true}
  });
  if(changed)persistRaceSummaryCache();
  return changed
}



