function isFeaturedBetRace(r,p){
  var title=String(r&&r.title||''),sel=null;
  try{sel=strictSelectedRaceProfile(r,p)}catch(e){}
  return !!(r&&(isMainForecastRace(r)||raceIsGraded(r)||
    (String(r.track||'')==='高知'&&(/ファイナル/i.test(title)||n(r.raceNumber)===12))||
    (sel&&sel.selected)||
    (window.ARVEXQMorningTicketLanes&&window.ARVEXQMorningTicketLanes.hasMorningPlace(r,morningPickOf(r)))))
}
