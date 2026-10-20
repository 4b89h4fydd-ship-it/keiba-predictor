function renderHomeSectionPage(){
  var page=state.homePage||'';
  if(page==='ai-stats')return smartDailyAiStatsPage();
  if(page==='favorites')return '<div class="smart-shell">'+smartTopBar(true,'お気に入りレース','保存したレース')+'<main class="smart-main smart-home-subpage arv-favorites-page">'+(favoriteHomeSection()||'<section class="arv-favorites-home"><p class="arv-favorites-empty">この日のお気に入りレースはありません。</p></section>')+'</main>'+cinematicFooter()+'</div>';
  if(page==='selected')return '<div class="smart-shell">'+smartTopBar(true,state.pickCircuit?(state.pickCircuit+' 厳選レース'):'厳選レース',state.pickCircuit?'本日の厳選':'中央 / 地方')+'<main class="smart-main smart-home-subpage">'+(state.pickCircuit?selectedCircuitPage(state.pickCircuit):homeCircuitChooser('厳選レース','selected'))+'</main>'+cinematicFooter()+'</div>';
  if(page==='special')return '<div class="smart-shell">'+smartTopBar(true,state.pickCircuit?(state.pickCircuit+' 特別予想'):'特別予想',state.pickCircuit?'重賞・高知ファイナル':'中央 / 地方')+'<main class="smart-main smart-home-subpage">'+(state.pickCircuit?specialCircuitPage(state.pickCircuit):homeCircuitChooser('特別予想','special'))+'</main>'+cinematicFooter()+'</div>';
  state.homePage=null;state.pickCircuit=null;return renderHome()
}
