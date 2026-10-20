function cinematicTabs(r){
  function tab(label,key){var active=state.openPanel===key;return '<button type="button" data-panel="'+key+'" aria-expanded="'+active+'" class="race-nav-v230-btn '+(active?'active':'')+'"><span class="race-nav-v230-label">'+label+'</span><span class="race-nav-v230-caret">'+(active?'−':'＋')+'</span></button>'}
  // v230: isolated navigation classes only. Do not inherit any legacy cinema-tabs sizing.
  return '<div class="race-nav-v230">'
    +'<div class="race-nav-v230-row race-nav-v230-top">'+tab('出走表','entry')+tab('展開予想','pace')+tab('買い目','bets')+'</div>'
    +'</div>'
}
