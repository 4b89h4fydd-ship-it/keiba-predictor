function paceStageJumpNav(active){
  return '<nav class="pace-stage-jump" aria-label="展開局面を直接選択">'
    +PACE_STAGE_PAGES.map(function(z,idx){return '<button type="button" data-pace-open="'+idx+'" class="'+(idx===active?'active':'')+'">'+esc(z.label)+'</button>'}).join('')
    +'</nav>'
}
