function mandatoryTrifectaRace(r){
  var title=String(r&&r.title||'');
  return !!(r&&(raceIsGraded(r)||(String(r.track||'')==='高知'&&(/ファイナル/i.test(title)||n(r.raceNumber)===12))))
}
// Only the independent strategy decides whether the reviewed 3連単 is adopted.
