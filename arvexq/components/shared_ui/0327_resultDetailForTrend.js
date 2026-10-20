function resultDetailForTrend(r){
  var id=String(r&&r.id||''),d=(id&&instantTrackDetails[id])||loadDetailCache(id)||null;
  if(d&&d.result&&(d.result.finishers||[]).length)return d;
  return r||{}
}
