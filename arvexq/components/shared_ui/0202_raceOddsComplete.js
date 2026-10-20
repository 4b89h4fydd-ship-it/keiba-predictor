function raceOddsComplete(r){
  var hs=(r&&r.horses||[]).filter(function(h){return !isScratchHorse(h)&&n(h.horseNumber)>0}),got=hs.filter(function(h){return n(h.winOdds)>0}).length;
  return !!hs.length&&got===hs.length
}
