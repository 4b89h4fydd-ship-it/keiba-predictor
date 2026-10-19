function raceHasOdds(r){return !!(r&&(r.horses||[]).some(function(h){return n(h.winOdds)>0}))}
