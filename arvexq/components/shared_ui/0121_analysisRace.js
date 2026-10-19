function analysisRace(r){
  var active=(r.horses||[]).filter(function(h){return !isScratchHorse(h)}).map(function(h){
    // Local official-margin evidence can arrive in recentRaces after allPastRuns was saved.
    // Keep both source arrays; historicalWindow deduplicates and merges actual proof.
    if(isObservedCircuit(r)){
      var recent=h.recentRaces||[],all=h.allPastRuns||[];
      if(raceMode(r)==='障害'){
        var jump=function(z){return /障害|ジャンプ|J[・･.]?G|\\bJS\\b/i.test((z.surface||'')+(z.title||''))};
        recent=recent.filter(jump);all=all.filter(jump)
      }
      return Object.assign({},h,{recentRaces:recent,allPastRuns:all})
    }
    var runs=h.allPastRuns||h.recentRaces||[];
    if(raceMode(r)==='障害')runs=runs.filter(function(z){return /障害|ジャンプ|J[・･.]?G|\bJS\b/i.test((z.surface||'')+(z.title||''))});
    return Object.assign({},h,{recentRaces:runs,allPastRuns:runs})
  });
  return Object.assign({},r,{horses:active,fieldSize:active.length||n(r.fieldSize)})
}


// v345: immutable *displayed* marks, independent of live odds, body weight
// refresh and the mutable winner model.  The server pre-race archive is preferred
// after the off.  A local device freeze is recorded BEFORE the scheduled start.
