function paceStagePendingPage(r){
  var cfg=paceStageConfig(state.paceStage);
  return '<div class="smart-shell pace-stage-shell">'+paceStageTopBar(r,cfg)
    +'<main class="smart-main smart-race-page pace-stage-page">'+paceStageJumpNav(cfg.index)
    +'<section class="card"><div class="empty">展開データを計算中です。</div></section></main>'+cinematicFooter()+'</div>'
}
