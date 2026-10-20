function observedHistory(h,r){
  var runs=historicalWindow(h,r);
  if(!isNarRace(r)){
    var jump=raceMode(r)==='障害';
    runs=runs.filter(function(q){
      var mode=String(q.surface||'')+' '+String(q.title||'');
      return /障害|ジャンプ|J[・･.]?G|\bJS\b/i.test(mode)===jump;
    });
  }
  return runs;
}

