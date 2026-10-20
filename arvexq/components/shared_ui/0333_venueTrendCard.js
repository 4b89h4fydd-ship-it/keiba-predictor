function venueTrendCard(){
  var t=venueTodayTrend(),caption=t.completed?String(t.completed)+'R集計・自動更新':'結果待ち・自動更新';
  return '<section class="smart-venue-trend"><div class="smart-venue-trend-head"><b>本日の傾向</b><small>'+esc(caption)+'</small></div><div class="smart-venue-trend-grid">'+
    '<div><small>トラックバイアス</small><strong>'+esc(t.bias)+'</strong></div>'+ 
    '<div><small>脚質</small><strong>'+esc(t.style)+'</strong></div>'+ 
    '<div><small>好走枠</small><strong>'+esc(t.frames)+'</strong></div>'+ 
  '</div></section>'
}
