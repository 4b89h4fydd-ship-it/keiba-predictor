function selectedCircuitPage(circuit){
  var picks=selectedRaceCandidates(circuit),body=picks.length?picks.map(function(z){var r=z.race,t=z.selection||{};return '<button type="button" class="fixed-pick-row arv-direct-pick-row" data-race="'+esc(r.id)+'"><span><b>'+esc(r.track)+' '+esc(r.raceNumber)+'R</b><small>'+esc(r.title||'')+'</small><small>'+esc(t.reason||'朝の固定判定')+'</small></span><time>'+esc(r.startTime||'--:--')+'</time><em>'+esc(t.primaryType||'厳選')+(t.noAxis?'｜軸なし・相手上位評価':'')+'｜'+esc((t.types||[]).filter(function(x){return x!==t.primaryType}).join('・')||t.score||'—')+'</em></button>'}).join(''):fixedPickEmpty('selected',circuit);

  return '<section class="smart-fixed-picks arv-direct-picks"><div class="smart-fixed-picks-head"><span><b>'+esc(circuit)+' 厳選レース</b><small>発走前の印・馬番入り買い目を保存確認</small></span><em>'+picks.length+'レース</em></div><div class="fixed-pick-box-body">'+body+'</div></section>'
}
