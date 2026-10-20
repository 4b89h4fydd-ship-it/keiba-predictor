function morningSavedMarkRows(r){
  // A pre-off loading/partial racecard must not display archived marks as live AI output.
  // Verified receipts may be shown after the off only for historical review.
  var snap=raceMarkClock(r).started?authorizedPreOffMarks(r):null,byNo={};
  if(snap&&Array.isArray(snap.horses)){
    snap.horses.forEach(function(z){byNo[n(z&&z.horseNumber,0)]=z})
  }
  return (r.horses||[]).filter(function(h){return h&&n(h.horseNumber)>0}).map(function(h){
    var z=byNo[n(h.horseNumber)]||{};
    return {horse:h,predMark:isScratchHorse(h)?'':String(z.mark||''),
      predRank:999,singleWinSuitable:!!z.singleWinSuitable};
  })
}
