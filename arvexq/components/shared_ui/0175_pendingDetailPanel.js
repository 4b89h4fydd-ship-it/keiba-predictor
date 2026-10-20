function pendingDetailPanel(r){
  var key=state.openPanel||'entry';if(key==='diagnosis')key='entry';var labels={entry:'出走表',pace:'展開予想',bets:'おすすめ買い目',result:'結果・払戻'},st=detailState(r.id),status=st[key==='bets'?'diagnosis':key]||'loading';
  if(key==='result')return resultPanel(r);
  return '<section class="card" data-section-state="'+esc(status)+'"><h2>'+esc(labels[key]||'出走表')+'</h2><p role="status">'+(status==='empty'?'出走馬0頭を確認しました。':(status==='error'?'この項目を取得できませんでした。取得済みの情報は表示を継続します。':'この項目を取得中です。'))+'</p>'+(status==='error'?'<button type="button" data-detail-retry="'+esc(r.id)+'">再試行</button>':'')+'</section>'
}
