function latestSavedForecastRevision(r){
  if(!r||!Array.isArray(r.forecastRevisions)||!r.currentForecastRevisionId)return null;
  var list=r.forecastRevisions.filter(function(v){return v&&v.version==='arvexq-forecast-revision-v1'&&
    v.revisionId===r.currentForecastRevisionId&&v.raceId===r.id&&v.raceDate===r.date&&Array.isArray(v.horses)});
  if(list.length!==1)return null;
  var v=list[0],seen={},valid=v.horses.every(function(h){var no=n(h.horseNumber);
    if(!no||seen[no]||['','◎','○','▲','△','☆','注'].indexOf(String(h.mark||''))<0)return false;
    seen[no]=true;return true});
  if(!valid||v.horses.filter(function(h){return h.mark==='◎'}).length>1)return null;
  var expected=(r.horses||[]).map(function(h){return n(h.horseNumber)});
  return expected.length===v.horses.length&&expected.every(function(no){return seen[no]})?v:null;
}
