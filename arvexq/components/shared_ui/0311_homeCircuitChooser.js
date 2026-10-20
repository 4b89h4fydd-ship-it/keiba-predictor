function homeCircuitChooser(title,kind){
  var rows=(state.races||[]),counts=homePickCounts(kind),buttons='',loading=!rows.length,
      pending=!morningPickReady();
  ['中央','地方'].forEach(function(circuit){
    var count=circuit==='中央'?counts.central:counts.local,
        status=loading?'取得中':(pending?'朝の判定待ち':'朝の確定選定');
    buttons+='<button type="button" class="arv-pick-circuit-btn" data-pick-circuit="'+circuit+'" aria-label="'+esc(circuit+' '+count+'件の'+title)+'"><span><small>'+esc(title)+'</small><b>'+esc(circuit)+'</b><em class="arv-pick-count">'+count+'件</em>'+(status?'<small class="arv-pick-count-pending">'+status+'</small>':'')+'</span><strong>›</strong></button>'
  });
  return '<section class="arv-pick-circuit-page"><div class="smart-section-title"><div><b>'+esc(title)+'</b><small>中央・地方ごとの該当件数</small></div></div><div class="arv-pick-circuit-grid">'+buttons+'</div>'+
    '</section>'
}
