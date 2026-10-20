function paceStageTopBar(r,cfg){
  var prev=cfg.index>0?'<button type="button" class="pace-stage-step prev" data-pace-open="'+(cfg.index-1)+'" aria-label="前の局面">‹</button>':'<span class="pace-stage-step ghost" aria-hidden="true"></span>',
      next=cfg.index<PACE_STAGE_PAGES.length-1?'<button type="button" class="pace-stage-step next" data-pace-open="'+(cfg.index+1)+'" aria-label="次の局面">›</button>':'<span class="pace-stage-step ghost" aria-hidden="true"></span>';
  return '<header class="smart-topbar smart-topbar-clean smart-race-topbar pace-stage-topbar">'
    +prev
    +'<div class="pace-stage-top-title"><strong>'+esc(cfg.label)+'</strong><small>'+esc(r.track)+' '+esc(r.raceNumber)+'R</small></div>'
    +next
    +'<button type="button" class="smart-race-close pace-stage-close" data-action="close-race-subpage" aria-label="4局面一覧へ戻る">×</button>'
    +'</header>'
}
