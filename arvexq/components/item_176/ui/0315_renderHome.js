function renderHome(){
  return '<div class="smart-shell smart-home">'+smartHomeHero()+'<main class="smart-main smart-home-main">'+(window.ARVEXQUnifiedHome?'<div class="arv-unified-body">'+window.ARVEXQUnifiedHome.dateBar(state.date)+window.ARVEXQUnifiedHome.buttons('horse'):'')+
    (window.ARVEXQHorsePortal?window.ARVEXQHorsePortal.home(state.races||[],{date:state.date,today:today(),nowMinutes:nowMins(),selected:homePickCounts('selected'),special:homePickCounts('special')}):
      '<section class="arv-all-panel"><header class="arv-all-title"><h2>各会場の全レース</h2></header><p class="arv-all-empty">出走データを読み込み中です。</p></section>')+
    (state.error?'<div class="notice">'+esc(state.error)+'</div>':'')+
    (window.ARVEXQUnifiedHome?'</div>':'')+
    '</main>'+cinematicFooter()+'</div>'
}
