function horseDetailPage(r,p){
  var rows=sortedHorseRows(p.rows||[]),no=n(state.detailHorseNo,0),idx=rows.findIndex(function(z){return n(z.horse&&z.horse.horseNumber)===no});
  if(idx<0&&rows.length){idx=0;state.detailHorseNo=n(rows[0].horse.horseNumber)}
  var x=idx>=0?rows[idx]:null,h=x&&x.horse||null,title=h?horseDisplayName(r,h):'馬詳細';
  return '<div class="smart-shell horse-detail-page-shell">'
    +'<header class="smart-topbar smart-topbar-clean smart-race-topbar horse-detail-topbar">'
      +'<button type="button" class="horse-detail-step" data-detail-prev="1" aria-label="前の馬">‹</button>'
      +'<div class="horse-detail-top-title"><strong>'+(h?esc(h.horseNumber)+'　'+esc(title):'馬詳細')+'</strong><small>'+esc(r.track)+' '+esc(r.raceNumber)+'R</small></div>'
      +'<button type="button" class="horse-detail-step" data-detail-next="1" aria-label="次の馬">›</button>'
      +'<button type="button" class="smart-race-close horse-detail-close" data-action="close-race-subpage" aria-label="出走表へ戻る">×</button>'
    +'</header>'
    +'<main class="smart-main smart-race-page horse-detail-page"><section class="card">'
    +(x&&p.legacyEngineDisabled?
      '<h2>'+esc(h.name||'')+'</h2><p>新方式の予想は未保存です。過去走の事実のみ表示します。</p>'+
      window.ARVEXQPastRunView.recentRows(h,r,esc):
      (x?runnerDetailBody(r,p,x):'<div class="empty">馬情報を取得中です。</div>'))
    +'</section></main>'+cinematicFooter()+'</div>'
}
