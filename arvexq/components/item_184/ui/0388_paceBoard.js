function paceBoard(r,p){
  return '<section class="card ai-flow-card pace-stage-menu-card">'
    +'<div class="ai-flow-head"><span class="ai-flow-bars"><i></i><i></i><i></i></span><div class="ai-flow-copy"><div class="ai-flow-title">AI展開予想</div><div class="ai-flow-sub">展開結論を確認し、4局面から直接開けます。</div></div></div>'
    +paceOutcomeSection(r,p)
    +paceStageMenu(r,p)
    +'</section>'
}
