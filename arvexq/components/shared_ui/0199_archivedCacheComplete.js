function archivedCacheComplete(r){
  if(!r)return false;
  var hs=r.horses||[],withHist=hs.filter(function(h){return (h.recentRaces||[]).length>0}).length,
      historyOk=r.analysisMode==='新馬'||!hs.length||withHist>=Math.max(2,Math.ceil(hs.length*.5)),
      oddsOk=raceHasOdds(r),diagOk=diagnosisCurrent(r);
  return historyOk&&diagOk&&oddsOk
}
