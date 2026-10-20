function fixedPickEmpty(kind,circuit){
  if(!morningPickReady())return '<div class="fixed-pick-empty"><b>朝の選定未確定</b><small>全レースを朝に一度だけ判定。発走後に選定を追加しません。</small></div>';
  var st=fixedPickLoadStatus(circuit),label='厳選判定';
  // Missing late detail data must not change the already published morning list.
  var incomplete=(state.races||[]).filter(function(r){return r&&String(r.circuit||'')===String(circuit)&&morningPickOf(r)&&morningPickOf(r).assessed===false}).length;
  return '<div class="fixed-pick-empty"><b>該当なし</b><small>'+(incomplete?('基準を満たす確定候補なし｜情報不足 '+incomplete+'レース（朝の未判定を後付けしません）'):(label+'基準を通過したレースなし'))+'</small></div>'
}
