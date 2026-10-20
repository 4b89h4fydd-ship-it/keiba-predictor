function venueTopBar(hi){
  return '<header class="smart-venue-topbar">'+
    '<span class="smart-pull-space" aria-hidden="true"></span>'+ 
    '<div class="smart-venue-topcopy"><strong>'+esc((state.track||'開催場')+' 全レース')+'</strong><small>'+esc((hi&&hi.status)||'')+'</small></div>'+ 
    '<button class="smart-venue-close" data-action="back" aria-label="トップへ戻る">×</button>'+ 
  '</header>'
}
