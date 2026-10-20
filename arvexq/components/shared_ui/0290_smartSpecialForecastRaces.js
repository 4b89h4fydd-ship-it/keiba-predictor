function smartSpecialForecastRaces(forceOpen){
  if(typeof state.specialForecastOpen!=='boolean'){
    try{state.specialForecastOpen=localStorage.getItem('arvexq-special-forecast-open')!=='0'}catch(e){state.specialForecastOpen=true}
  }
  var picks=specialForecastRaceCandidates(),body=picks.length?picks.map(function(r){
    var tag=specialForecastRaceTag(r);
    return '<button type="button" class="fixed-pick-row" data-race="'+esc(r.id)+'"><span><b>'+esc(r.track)+' '+esc(r.raceNumber)+'R</b><small>'+esc(r.title||'')+'</small></span><time>'+esc(r.startTime||'--:--')+'</time><em>'+tag+'</em></button>'
  }).join(''):'<div class="fixed-pick-empty"><b>該当なし</b><small>本日のメイン・重賞・高知ファイナルなし</small></div>';
  return '<details class="smart-fixed-picks smart-special-picks" data-special-fold="1"'+((forceOpen||state.specialForecastOpen)?' open':'')+'><summary class="smart-fixed-picks-head"><span><b>特別予想</b><small>メイン・重賞・高知ファイナル｜朝固定</small></span><span class="smart-fixed-summary-right"><em>'+picks.length+'レース</em><i class="special-fold-icon" aria-hidden="true">›</i></span></summary><div class="smart-fixed-pick-grid"><div class="fixed-pick-box fixed-pick-circuit"><div class="fixed-pick-box-body">'+body+'</div></div></div></details>'
}

