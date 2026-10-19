function paceOutcomeModel(r,p){
  var rows=(p&&p.rows||[]).slice(),plan=activeScenarioPlan(p)||p.plan||{},stages=visiblePaceStages(plan),
      straight=stages.find(function(s){return s&&s.key==='straight'})||stages[stages.length-1]||{},pack=straight.pack||[],byNo={},i;
  rows.forEach(function(x){byNo[n(x.horse&&x.horse.horseNumber)]=x});
  if(!rows.length)return null;
  var order=pack.map(function(z){return byNo[n(z.no)]}).filter(Boolean);
  rows.forEach(function(x){if(order.indexOf(x)<0)order.push(x)});
  var day={active:false,flowLabel:'中立',byNo:{},policy:'past-results-do-not-revise-pace-or-marks'},sc=plan.scenario||{},arr=p.arrangement||{},
      leader=((plan.start||[])[0])||(arr.leadCandidates||[])[0]||null,field=Math.max(1,order.length),rankByNo={};
  order.forEach(function(x,idx){rankByNo[n(x.horse.horseNumber)]=idx+1});
  rows.forEach(function(x){
    var no=n(x.horse.horseNumber),rank=n(rankByNo[no],field),pos=field<=1?1:1-(rank-1)/(field-1),dc=(day.byNo||{})[no]||{},
        win=n(x.winnerDecisionProbability,n(x.winnerConsensusProbability,n(x.p1Probability,.5))),
        p2=n(x.p2RecallScore,n(x.p2Probability,.5)),p3=n(x.p3RecallScore,n(x.p3Probability,.5));
    x._paceOutcomeFirst=clamp(pos*.58+win*.22+n(x.ability,.5)*.10+n(x.frontStay,.5)*.05+n(x.comeFromBehind,.5)*.05+n(dc.winBoost,0)*2,0,1);
    x._paceOutcomeSecond=clamp(pos*.42+p2*.33+n(x.posCons,.5)*.10+n(x.latePower,.5)*.08+n(x.frontStay,.5)*.07+n(dc.p2Boost,0)*2,0,1);
    x._paceOutcomeThird=clamp(pos*.34+p3*.36+n(x.latePower,.5)*.12+n(x.move,.2)*.08+n(x.posCons,.5)*.10+n(dc.p3Boost,0)*2,0,1);
    x.paceOutcomeFirst=x._paceOutcomeFirst;x.paceOutcomeSecond=x._paceOutcomeSecond;x.paceOutcomeThird=x._paceOutcomeThird
  });
  var top=order[0]||null,firstGroup=top?[top]:[],secondGroup=order.slice(1,Math.min(4,order.length)),thirdGroup=order.slice(2,Math.min(6,order.length)),
      leaderNo=n(leader&&leader.horse&&leader.horse.horseNumber),winnerNo=n(top&&top.horse&&top.horse.horseNumber),leaderRow=byNo[leaderNo]||leader||null,
      winnerStyle=String(top&&(top.expected||top.pastStyle)||''),verdict='好位抜け出し',ctx=p.minetaContext||null;
  if(top){
    if(winnerNo===leaderNo&&n(top.frontStay)>=Math.max(.52,n(top.comeFromBehind)-.03))verdict='逃げ切り';
    else if(winnerStyle.indexOf('後方')>=0||winnerStyle.indexOf('追')>=0)verdict='追い込み';
    else if(winnerStyle.indexOf('中団')>=0||winnerStyle.indexOf('差')>=0||n(top.comeFromBehind)>=n(top.frontStay)+.05)verdict='差し切り';
    else if(winnerStyle.indexOf('先行')>=0||winnerStyle.indexOf('好位')>=0)verdict='先行押し切り'
  }
  var leadRank=leaderRow?order.indexOf(leaderRow)+1:0,reason=[];
  reason.push('ハナ想定 '+(leaderRow?rowName(leaderRow):'不明'));
  if(ctx)reason.push(minetaStructureText(ctx));
  if(day.active)reason.push('当日バイアス '+day.flowLabel);
  if(winnerNo===leaderNo)reason.push('局面遷移で先頭を維持');
  else if(leaderRow)reason.push('逃げ馬はラスト'+leadRank+'番手、'+(top?rowName(top):'不明')+'が前へ');
  return{verdict:verdict,leader:leaderRow,winner:top,first:firstGroup,second:secondGroup,third:thirdGroup,margin:0,day:day,scenario:sc,reason:reason.join('｜'),order:order}
}
