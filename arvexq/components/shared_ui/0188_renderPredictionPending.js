function renderPredictionPending(r){
  var st=detailState(r.id),task=racePredictionTasks.get(r);
  if(!task&&!r._entryOnly){
    task={status:'loading'};racePredictionTasks.set(r,task);
    setTimeout(function(){
      try{predict(r);task.status='loaded';st.diagnosis='loaded';st.pace='loaded'}
      catch(error){task.status='error';st.diagnosis='error';st.pace='error';traceRaceDetail(r.id,'analysis-failed',{message:String(error&&error.message||error)})}
      if(state.race===r)render()
    },30)
  }
  if(!state.openPanel)state.openPanel='entry';
  if(state.subPage==='horse'){
    var hh=(r.horses||[]).find(function(z){return n(z.horseNumber)===n(state.detailHorseNo)})||{};
    return '<div class="smart-shell">'+raceSubpageTopBar(r,horseDisplayName(r,hh))+'<main class="smart-main smart-race-page"><section class="card"><div class="empty">馬情報を取得中です。</div></section></main>'+cinematicFooter()+'</div>'
  }
  if(state.subPage==='bets')return frozenAiBetForRace(r)?betDetailPage(r,{rows:morningSavedMarkRows(r)}):'<div class="smart-shell">'+raceSubpageTopBar(r,'おすすめ買い目')+'<main class="smart-main smart-race-page"><section class="card"><div class="empty">発走前の買い目原本が未取得です。取得後に表示します（発走後の再計算はしません）。</div></section></main>'+cinematicFooter()+'</div>';
  if(state.subPage==='pace-stage')return paceStagePendingPage(r);
  var content=state.openPanel==='entry'?safeEntryPanel(r,{rows:morningSavedMarkRows(r)}):(state.openPanel==='result'?resultPanel(r):pendingDetailPanel(r));
  return '<div class="smart-shell">'+smartRaceTopBar(r)+'<main class="smart-main smart-race-page">'+smartRaceHead(r)+cinematicTabs(r)+raceDetailNotice(r)+'<div class="smart-race-content">'+content+'</div></main>'+cinematicFooter()+'</div>'
}
