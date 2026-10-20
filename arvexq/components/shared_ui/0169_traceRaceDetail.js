function traceRaceDetail(id,event,extra){
  var item=Object.assign({raceId:String(id),event:event,at:Date.now()},extra||{});
  raceDetailTrace.push(item);if(raceDetailTrace.length>60)raceDetailTrace.shift();
  if(event==='failed')console.warn('[ARVEXQ race detail]',item)
}
