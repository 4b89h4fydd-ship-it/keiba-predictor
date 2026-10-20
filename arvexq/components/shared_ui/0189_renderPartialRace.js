function renderPartialRace(r){
  if(!state.openPanel)state.openPanel='entry';
  if(state.subPage==='horse'){
    var h=(r.horses||[]).find(function(z){return n(z.horseNumber)===n(state.detailHorseNo)})||{};
    return '<div class="smart-shell">'+raceSubpageTopBar(r,horseDisplayName(r,h))+'<main class="smart-main smart-race-page"><section class="card"><div class="empty">馬情報を取得中です。</div></section></main>'+cinematicFooter()+'</div>'
  }
  if(state.subPage==='bets')return frozenAiBetForRace(r)?betDetailPage(r,{rows:morningSavedMarkRows(r)}):'<div class="smart-shell">'+raceSubpageTopBar(r,'おすすめ買い目')+'<main class="smart-main smart-race-page"><section class="card"><div class="empty">発走前の買い目原本が未取得です。取得後に表示します（発走後の再計算はしません）。</div></section></main>'+cinematicFooter()+'</div>';
  if(state.subPage==='pace-stage')return paceStagePendingPage(r);
  return '<div class="smart-shell">'+smartRaceTopBar(r)+'<main class="smart-main smart-race-page">'+smartRaceHead(r)+cinematicTabs(r)+raceDetailNotice(r)+'<div class="smart-race-content">'+pendingDetailPanel(r)+'</div></main>'+cinematicFooter()+'</div>'
}
// Display the factual dated roster immediately, independently of Cloudflare D1.
// This never supplies odds, AI marks, betting evidence, or post-off results.
