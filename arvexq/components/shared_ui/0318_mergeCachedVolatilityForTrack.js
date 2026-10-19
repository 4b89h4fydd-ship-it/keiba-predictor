function mergeCachedVolatilityForTrack(track){
  var changed=false;
  state.races.forEach(function(r){
    if(r.circuit!==state.circuit||r.track!==track||!r.id)return;
    var d=loadDetailCache(r.id),v=d&&d.volatility;
    if(v&&v.version==='arvexq-volatility-v1'){
      if(JSON.stringify(r.volatility||null)!==JSON.stringify(v)){r.volatility=v;changed=true}
    }
  });
  if(changed)persistRaceSummaryCache();
  return changed
}
