function hydrateInstantFromDevice(rows){
  var count=0;
  (rows||[]).forEach(function(r){
    if(!r||!r.id)return;
    var d=loadDetailCache(r.id);
    if(d){instantTrackDetails[String(r.id)]=d;count++}
  });
  return count
}
