function mergeTrackPack(rows){
  var changed=false;
  (rows||[]).forEach(function(d){
    if(!d||!d.id)return;
    var id=String(d.id),old=instantTrackDetails[id]||loadDetailCache(id)||null,
        r=state.races.find(function(x){return String(x.id)===id}),merged=mergeRaceReflection(old,d,null,r||null);
    instantTrackDetails[id]=merged;saveDetailCache(id,merged);
    if(r&&merged.volatility){
      var before=JSON.stringify(r.volatility||null),after=JSON.stringify(merged.volatility);
      if(before!==after){r.volatility=merged.volatility;changed=true}
    }
  });
  return changed
}


