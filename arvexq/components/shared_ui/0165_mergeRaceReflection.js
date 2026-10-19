function mergeRaceReflection(base,incoming,oddsRows,summary){
  base=base||{};incoming=incoming||{};summary=summary||{};
  var out=Object.assign({},base);
  Object.keys(incoming).forEach(function(key){
    var v=incoming[key];
    if(key==='horses'||key==='result')return;
    if((key==='predictionModelVersion'||key==='predictionStatus'||key==='legacyPresentationDisabled')&&
       String(base.predictionModelVersion||'').indexOf('arvexq-learned-whole-career')===0&&
       String(incoming.predictionModelVersion||'')!==String(base.predictionModelVersion||''))return;
    if(reflectUseful(v))out[key]=v
  });
  Object.keys(summary).forEach(function(key){
    var v=summary[key];
    if(key==='horses'||key==='result')return;
    // Day summaries may be stale or built by the retired scorer. Only a
    // full detail can authoritatively replace its learned forecast version.
    if((key==='predictionModelVersion'||key==='predictionStatus'||key==='legacyPresentationDisabled')&&
       String(out.predictionModelVersion||'').indexOf('arvexq-learned-whole-career')===0&&
       String(summary.predictionModelVersion||'')!==String(out.predictionModelVersion||''))return;
    if(reflectUseful(v))out[key]=v
  });
  var combinedResult=mergePublishedResult(base.result,incoming.result);
  if(reflectUseful(combinedResult))out.result=combinedResult;
  var oldBy={},newBy={},liveBy={},order=[];
  (base.horses||[]).forEach(function(h){var no=n(h&&h.horseNumber,0);if(no){oldBy[no]=h;order.push(no)}});
  (incoming.horses||[]).forEach(function(h){var no=n(h&&h.horseNumber,0);if(no){newBy[no]=h;if(order.indexOf(no)<0)order.push(no)}});
  (oddsRows||[]).forEach(function(z){var q=edgeOddsRow(z),no=n(q.horseNumber,0);if(no){liveBy[no]=q;if(order.indexOf(no)<0)order.push(no)}});
  if(order.length){
    order.sort(function(a,b){return a-b});
    out.horses=order.map(function(no){return mergeHorseReflection(oldBy[no],newBy[no],liveBy[no])})
  }else if(Array.isArray(incoming.horses)&&incoming.fieldSize!=null&&Number(incoming.fieldSize)===0){out.horses=[]}
  if((oddsRows||[]).length){
    out.oddsUpdatedAt=String((oddsRows||[]).reduce(function(mx,z){return Math.max(mx,n(z&&((z.updatedAt!=null)?z.updatedAt:z.updated_at),0))},0)||out.oddsUpdatedAt||'');
    out.liveFieldsMerged=true
  }
  // A roster-first/static fallback is not permanent. Once the authoritative
  // detail supplies dated horse histories, let the normal pre-off mark engine
  // start; otherwise the inherited _entryOnly flag suppresses predictions.
  // A partial roster/odds-only response must not clear the gate.
  var fullHistoryReceived=Array.isArray(incoming.horses)&&incoming.horses.some(function(h){
    return h&&((Array.isArray(h.recentRaces)&&h.recentRaces.length>0)||
      (Array.isArray(h.allPastRuns)&&h.allPastRuns.length>0));
  });
  if(fullHistoryReceived){
    out._entryOnly=false;
    delete out._staticRacecardFallback;
  }
  if(typeof window!=='undefined'&&window.ARVEXQRaceIdentity)out=window.ARVEXQRaceIdentity.sanitize(out);
  return mergeResultHorseFields(out)
}
