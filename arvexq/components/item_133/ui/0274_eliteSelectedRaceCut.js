function eliteSelectedRaceCut(rows){
 if(!window.ARVEXQMorningSelection||!window.ARVEXQMorningSelection.allStrictQualifiers)
   throw Error('morning selection module missing; refuse an incomplete morning freeze');
 return window.ARVEXQMorningSelection.allStrictQualifiers(rows,{n:n,chronological:raceChronologicalCompare});
}
