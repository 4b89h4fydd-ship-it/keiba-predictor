function paceStageNarrative(p,key){
  var rows=p.rows||[],arr=p.arrangement||{},order=paceStageRows(p,key),plan=activeScenarioPlan(p)||p.plan||{},out=p.outcome||null,
      byNo={},i;rows.forEach(function(x){byNo[n(x.horse&&x.horse.horseNumber)]=x});
  if(!order.length)return '展開データを準備中です。';
  var leader=order[0],second=order[1]||null,third=order[2]||null,fourth=order[3]||null,tail=order[order.length-1]||null,
      leadNo=n(leader&&leader.horse&&leader.horse.horseNumber),secondNo=n(second&&second.horse&&second.horse.horseNumber),
      front2=[third,fourth].filter(Boolean),midStart=Math.min(4,Math.max(2,order.length-3)),midEnd=Math.max(midStart,order.length-1),
      middle=order.slice(midStart,midEnd),leadCandidates=(arr.leadCandidates||[]).filter(Boolean).slice(0,3),
      text=[],prevKey=key==='turn3'?'back':(key==='turn4'?'turn3':(key==='straight'?'turn4':'')),prev=prevKey?paceStageRows(p,prevKey):[],
      prevRank={},rank={},gainers=[],droppers=[];
  prev.forEach(function(x,j){prevRank[n(x.horse.horseNumber)]=j+1});
  order.forEach(function(x,j){rank[n(x.horse.horseNumber)]=j+1});
  rows.forEach(function(x){var no=n(x.horse.horseNumber),a=n(prevRank[no],0),b=n(rank[no],0);if(a&&b&&a-b>=2)gainers.push(x);if(a&&b&&b-a>=2)droppers.push(x)});

  if(key==='start'){
    var contenders=leadCandidates.length>=2?leadCandidates:order.slice(0,Math.min(2,order.length)),
        settled=paceStageRows(p,'first'),settledLeader=settled[0]||leader,
        secondLine=settled.slice(1,Math.min(3,settled.length)),
        nextLine=settled.slice(3,Math.min(5,settled.length)),
        midSettled=settled.slice(5,Math.max(5,settled.length-1)),
        tailSettled=settled[settled.length-1]||tail;
    if(contenders.length>=2)text.push(paceNosText(contenders)+'がハナ争い');
    text.push(n(settledLeader&&settledLeader.horse&&settledLeader.horse.horseNumber)+'がハナ');
    // Expose the data behind the claim; first-corner occupancy is NOT measured
    // gate reaction or first-1F time. Show sample sizes to avoid false certainty.
    contenders.slice(0,Math.min(3,contenders.length)).forEach(function(z){
      var ph=z.minetaPast||minetaPastProfile(z.horse,state.race||{}),cnt=n(ph.firstCornerSamples,0);
      if(cnt)text.push(n(z.horse.horseNumber)+'の近走初角先頭 '+Math.round(n(ph.leadRate)*100)+'%（'+cnt+'走）');
      var timing=z.earlyTimingProfile||{},observed=(timing.samples||[]).filter(function(e){return e.first200mSeconds!=null||e.gateReactionSeconds!=null});
      if(observed.length){
        var one=observed[0],kind=one.kind==='individual_sensor'?'個別センサー':'映像推定';
        text.push(n(z.horse.horseNumber)+'の'+kind+'（'+one.date+'）：'+(one.first200mSeconds!=null?'個別テン1F '+one.first200mSeconds.toFixed(2)+'秒':'テン1F未取得')+(one.gateReactionSeconds!=null?'、ゲート反応 '+one.gateReactionSeconds.toFixed(2)+'秒':'')+'。取得元 '+one.source)
      }
    });
    if(secondLine.length)text.push('2番手集団 '+paceNosText(secondLine));
    if(nextLine.length)text.push('その後ろ '+paceNosText(nextLine));
    if(midSettled.length>=2)text.push('中団 '+paceNosText(midSettled));
    else if(midSettled.length===1)text.push('中団 '+paceNosText(midSettled));
    if(tailSettled&&settled.length>5)text.push('しんがり '+n(tailSettled.horse.horseNumber));
    return text.join(' → ')
  }

  if(key==='turn3'){
    text.push(leadNo+'が先頭');
    if(secondNo)text.push(secondNo+'が2番手で追走');
    if(gainers.length)text.push(paceNosText(gainers.slice(0,3))+'が中団から進出');
    else text.push('前の隊列は大きく変わらず');
    var hold=order.filter(function(x){return n(x.horse.horseNumber)!==leadNo&&x.move<.52&&x.comeFromBehind>=.52}).slice(-2);
    if(hold.length)text.push(paceNosText(hold)+'はまだ脚をためる');
    if(tail)text.push(n(tail.horse.horseNumber)+'は後方待機');
    return text.join(' → ')
  }

  if(key==='turn4'){
    text.push(leadNo+'が先頭で直線へ');
    if(secondNo)text.push(secondNo+'が直後');
    if(gainers.length)text.push(paceNosText(gainers.slice(0,3))+'が進出して前との差を詰める');
    var attack=order.filter(function(x){return n(x.horse.horseNumber)!==leadNo&&(x.comeFromBehind>=.56||x.latePower>=.58)}).slice(0,3);
    if(attack.length)text.push(paceNosText(attack)+'は差し・追い込み態勢');
    if(droppers.length)text.push(paceNosText(droppers.slice(0,2))+'は手応え注意');
    if(tail)text.push('最後方'+n(tail.horse.horseNumber)+'も直線勝負');
    return text.join(' → ')
  }

  if(key==='straight'){
    out=out||paceOutcomeModel(state.race||{},p);
    var winner=out&&out.winner?out.winner:leader,winnerNo=n(winner&&winner.horse&&winner.horse.horseNumber),
        verdict=String(out&&out.verdict||''),chasers=order.slice(1,Math.min(4,order.length)),
        closers=rows.filter(function(x){return x!==winner&&(x.comeFromBehind>=.56||x.latePower>=.58)}).sort(function(a,b){return n(rank[n(a.horse.horseNumber)],99)-n(rank[n(b.horse.horseNumber)],99)}).slice(0,3);
    if(winnerNo===leadNo&&/逃げ切り/.test(verdict))text.push(leadNo+'がハナのまま逃げ切り態勢');
    else if(winnerNo!==leadNo)text.push(leadNo+'が粘るが、'+winnerNo+'が'+(verdict||'抜け出し')+'本線');
    else text.push(winnerNo+'が先頭で押し切り態勢');
    if(chasers.length)text.push(paceNosText(chasers)+'が後ろから追う');
    var stalkAttack=chasers.filter(function(x){return x.expected==='先行'||x.expected==='好位'||x.stalk>=.28}).slice(0,3);
    if(stalkAttack.length)text.push(paceNosText(stalkAttack)+'は脚をためて差しを狙う');
    if(closers.length)text.push(paceNosText(closers)+'が追い込みを仕掛ける');
    if(tail&&closers.indexOf(tail)>=0)text.push('しんがり'+n(tail.horse.horseNumber)+'も大外から追い込み');
    return text.join(' → ')
  }
  return ''
}
