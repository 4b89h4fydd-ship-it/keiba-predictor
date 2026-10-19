function raceSubpageTopBar(r,title){
  return '<header class="smart-topbar smart-topbar-clean smart-race-topbar smart-race-subpage-topbar">'
    +'<button type="button" class="smart-race-step prev" data-action="close-race-subpage" aria-label="レースへ戻る">&lt;</button>'
    +'<div class="smart-head-copy smart-head-copy-clean smart-race-head-copy"><strong>'+esc(title||'詳細')+'</strong><small>'+esc(r.track)+' '+esc(r.raceNumber)+'R</small></div>'
    +'<button type="button" class="smart-race-close" data-action="close-race-subpage" aria-label="閉じる">×</button>'
    +'</header>'
}
