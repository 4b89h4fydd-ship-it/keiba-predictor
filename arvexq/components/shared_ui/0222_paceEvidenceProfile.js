function paceEvidenceProfile(r,p){
  var entries=((p&&p.rows)||[]).filter(function(z){return z&&z.horse&&!isScratchHorse(z.horse)}),
      date=String((r&&r.date)||''),counts={},valid=0,leaderNos={},i;
  // Use the exact same five-race, de-duplicated pre-race source as the
  // development engine. A stored five-row history may have zero valid corners.
  entries.forEach(function(z){
    var no=n(z.horse.horseNumber,0),runs=paceHistoryRuns(z.horse,r);
    counts[no]={history:runs.length,earlyPositions:runs.length};
    if(runs.length>=2)valid++
  });
  ((p&&p.arrangement&&p.arrangement.leadCandidates)||[]).slice(0,2).forEach(function(z){
    var no=n(z&&z.horse&&z.horse.horseNumber,0);if(no)leaderNos[no]=1
  });
  var ranked=entries.slice().sort(function(a,b){
    return n(b.winnerDecisionProbability,n(b.winnerConsensusProbability,n(b.p1Probability)))-
      n(a.winnerDecisionProbability,n(a.winnerConsensusProbability,n(a.p1Probability)))
  });
  var top=ranked.slice(0,Math.min(3,ranked.length)),topMissing=top.filter(function(z){
    var q=counts[n(z.horse.horseNumber)]||{};
    return n(q.earlyPositions)<2||n(q.history)<3
  }).map(function(z){return n(z.horse.horseNumber)});
  var leaderMissing=Object.keys(leaderNos).filter(function(no){
    return n((counts[no]||{}).earlyPositions)<2
  }).map(Number);
  var coverage=entries.length?valid/entries.length:0,
      sufficient=entries.length>=4&&coverage>=.55&&!topMissing.length&&!leaderMissing.length;
  var reasons=[];
  if(coverage<.55)reasons.push('全頭の初角通過順位が不足');
  if(topMissing.length)reasons.push('上位馬'+topMissing.join('・')+'の先行根拠不足');
  if(leaderMissing.length)reasons.push('ハナ候補'+leaderMissing.join('・')+'の先行根拠不足');
  if(!date)reasons.push('対象日を確認できない');
  return{ready:sufficient,coverage:coverage,topMissing:topMissing,leaderMissing:leaderMissing,
    observedHorses:valid,totalHorses:entries.length,reason:reasons.join('／')||'過去走の初角通過順位を確認',
    source:'過去走初角順位による位置取り推定（実測テン1Fではない）'};
}
