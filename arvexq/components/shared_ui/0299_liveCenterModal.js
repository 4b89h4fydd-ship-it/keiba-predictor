function liveCenterModal(){
  if(!liveCenterOpen)return '';
  var rows=liveVenueOptions();
  var locals=rows.filter(function(v){return String(v.circuit||'')==='地方'});
  var jra=liveVenueExternal('中央','');
  var localBody=locals.length?locals.map(function(v){
    return '<a class="live-direct-venue" href="'+esc(liveVenueExternal('地方',v.track))+'" target="_blank" rel="noopener noreferrer"><small>地方</small><b>'+esc(v.track)+'</b><strong>›</strong></a>'
  }).join(''):'<div class="live-center-empty">本日の地方開催場はありません</div>';
  return '<div class="live-center-overlay" data-live-key="direct" role="dialog" aria-modal="true" aria-label="ライブ中継">'+
    '<div class="live-center-sheet live-direct-sheet">'+
      '<header class="live-center-head"><div><b>LIVE</b><small>公式ライブへ移動</small></div><button type="button" data-action="live-close" aria-label="閉じる">×</button></header>'+
      '<div class="live-direct-menu">'+
        '<a class="live-direct-box central" href="'+esc(jra)+'" target="_blank" rel="noopener noreferrer"><span><small>中央競馬</small><b>中央</b></span><em>JRA公式LIVEへ</em><strong>›</strong></a>'+
        '<details class="live-direct-local"><summary class="live-direct-box local"><span><small>地方競馬</small><b>地方</b></span><em>開催場を選ぶ</em><strong>＋</strong></summary><div class="live-direct-venues">'+localBody+'</div></details>'+
      '</div>'+
    '</div></div>'
}
