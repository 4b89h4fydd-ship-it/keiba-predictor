function volatilityBadge(r){
  var v=r&&r.volatility||{},ready=v.ready===true&&n(v.score)>0,label=ready?String(v.label||'標'):'…',
      cls=ready?(' vol-'+(label==='硬'?'hard':label==='標'?'standard':label==='荒'?'rough':'wild')):' vol-pending',
      title=ready?('荒れ度 '+n(v.score)+'/18'+((v.reasons||[]).length?'・'+(v.reasons||[]).join(' / '):'')):'荒れ度を内部計算中';
  return '<span class="race-vol-badge'+cls+'" title="'+esc(title)+'"><small>荒れ度</small><b>'+esc(label)+'</b></span>'
}

