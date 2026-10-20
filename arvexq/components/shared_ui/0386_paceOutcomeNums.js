function paceOutcomeNums(list){return(list||[]).map(function(x){return n(x.horse&&x.horse.horseNumber)}).filter(Boolean).join('・')||'—'}
