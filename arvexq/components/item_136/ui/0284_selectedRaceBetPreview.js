function selectedRaceBetPreview(r){
  var d=instantTrackDetails[String(r.id)]||loadDetailCache(r.id),st=mins(r.startTime),started=r.date===today()&&st<9999&&nowMins()>=st,
      source=mergeRaceReflection(r,d,null,null),plan=frozenAiBetForRace(source),p=null;
  if(plan)plan=immutableStoredAiBetView(source,plan);
  if(d&&!plan&&!isFinal(d)&&!started){try{p=predict(d);plan=buildAiBetPlan(d,p)}catch(e){}}
  if(!plan)return '<div class="selected-bet-pending">発走前の馬番入り買い目原本が未保存・未取得です。結果から作り直しません。</div>';
  if(plan.decision==='見送り')return '<div class="selected-bet-pending">ARVEXQ買い目　見送り（'+esc(plan.betQuality||0)+'/100）</div>';
  var lines=(plan.items||[]).map(function(z){var comboText=z.combo||betComboText(z.kind,z.combos||[]);return '<span class="selected-bet-chip '+(z.kind==='3連単'?'tri':'')+'"><b>おすすめ買い目</b> '+esc(z.kind)+' '+esc(comboText)+'</span>'}).join('');if(plan.trifectaReviewed&&plan.trifectaDecision==='見送り')lines+='<span class="selected-bet-chip tri"><b>3連単</b> 検討済み・見送り</span>';
  var result='';if(d&&isFinal(d)){var hit=aiBetPlanHit(d,plan),lv=hit&&hit.levels||{},hits=[];['本線','保険'].forEach(function(k){if(lv[k])hits.push(k+'HIT')});result='<div class="selected-result '+(hit&&hit.hit?'hit':'miss')+'">結果　'+(hits.length?hits.join(' / '):'通常買い目不的中')+(hit&&hit.tri?'　<strong>3連単HIT</strong>':'')+'</div>'}
  return '<div class="selected-bets">'+lines+'</div>'+result
}
