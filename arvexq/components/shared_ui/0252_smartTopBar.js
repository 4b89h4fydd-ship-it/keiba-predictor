function smartTopBar(back,title,sub){
  // One dated subpage header for both sports. Retire the previous empty spacer.
  if(state.homePage&&!state.track&&!state.race){
    return '<header class="smart-topbar smart-topbar-clean smart-section-topbar arv-dated-subbar">'+
      '<button type="button" class="arv-sub-back" data-action="back" aria-label="戻る">‹</button>'+
      '<div class="smart-head-copy smart-head-copy-clean"><strong>'+esc(String(title||'').replace(/^本日の/,''))+'</strong></div>'+
      '<label class="arv-sub-date"><span>'+esc(state.date.replace(/-/g,'/'))+'</span>'+
      '<input type="date" id="date" value="'+esc(state.date)+'" aria-label="厳選・特別・AI成績の表示日を変更"></label>'+
      '<button type="button" class="arv-sub-close" data-home-close="1" aria-label="トップへ戻る">×</button>'+
      '</header>'
  }
  return '<header class="smart-topbar smart-topbar-clean smart-section-topbar">'+
    '<span class="smart-pull-space" aria-hidden="true"></span>'+ 
    '<div class="smart-head-copy smart-head-copy-clean"><strong>'+esc(title||'開催場')+'</strong><small>'+esc(sub||'')+'</small></div>'+ 
    (back?'<button class="smart-section-close" data-action="back" aria-label="トップへ戻る">×</button>':'<span class="smart-back-space"></span>')+
  '</header>'
}
