function smartRaceHead(r){
  var count=raceHeadCountText(r),markState='';
  return '<section class="smart-race-head smart-race-head-compact smart-race-head-v222">'+
    '<div class="smart-race-title-stack smart-race-full-title"><div class="arv-favorite-title-row"><h1>'+esc(r.title||'レース詳細')+'</h1>'+favoriteStarHtml(r,'arv-detail-favorite-star')+'</div>'+(markState?'<small class="arv-mark-fix-status">'+esc(markState)+'</small>':'')+'</div>'+
    '<div class="smart-race-head-layout">'+
      '<div class="smart-race-left-stack">'+
        '<div class="smart-race-head-left"><span class="smart-circuit-chip">'+esc(r.circuit||state.circuit)+'</span><div class="smart-race-title-stack"><div class="smart-race-meta">'+esc(r.surface||'')+' '+esc(r.distance||'—')+'m　'+esc(r.weather||'')+' '+esc(r.condition||'')+'　'+count+'</div></div>'+cinematicGrade(r)+'</div>'+
        officialRaceActions(r)+
      '</div>'+ 
      '<div class="smart-race-result-side"><time>'+timeHtml(r)+' 発走</time>'+smartInlineResult(r)+'</div>'+ 
    '</div>'+ 
  '</section>'
}
