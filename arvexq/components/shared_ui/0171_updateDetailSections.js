function updateDetailSections(id,r,received){
  var st=detailState(id),hs=r&&r.horses||[],hasEntries=hs.some(function(h){return h&&n(h.horseNumber)>0&&String(h.name||'').trim()}),missing=st.error?'error':'loading';
  st.basic=r&&r.id?'loaded':missing;
  st.entry=hasEntries?'loaded':(received&&Array.isArray(r&&r.horses)&&r.fieldSize!=null&&Number(r.fieldSize)===0?'empty':missing);
  st.odds=hs.some(function(h){return n(h&&h.winOdds)>0})?'loaded':missing;
  st.history=hs.some(function(h){return h&&((h.recentRaces||[]).length||(h.allPastRuns||[]).length)})?'loaded':(hasEntries&&hs.every(function(h){return h.debutNoHistory})?'empty':missing);
  st.diagnosis=r&&r._prediction?'loaded':missing;st.pace=r&&r._prediction?'loaded':missing;
  st.result=hasAnyResultData(r||{})?'loaded':(r&&!isFinal(r)&&!isFlash(r)?'empty':missing);
  st.payouts=r&&r.result&&(r.result.payouts||[]).length?'loaded':missing;
  return st
}
