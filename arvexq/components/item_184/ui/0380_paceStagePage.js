function paceStagePage(r,p){
  var cfg=paceStageConfig(state.paceStage);
  return '<div class="smart-shell pace-stage-shell">'+paceStageTopBar(r,cfg)
    +'<main class="smart-main smart-race-page pace-stage-page">'+paceStageJumpNav(cfg.index)
      +paceStageEvidence(p,cfg)+paceFormationDiagram(r,p,cfg)
    +'</main>'+cinematicFooter()+'</div>'
}
