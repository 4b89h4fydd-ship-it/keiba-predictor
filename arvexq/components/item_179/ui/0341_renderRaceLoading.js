function renderRaceLoading(){
  var row=state.races.find(function(x){return String(x.id)===String(state.raceLoading)});
  return '<div class="smart-shell">'+
    (row?smartRaceTopBar(row):smartTopBar(true,state.track||'レース','レース詳細'))+
    '<main class="smart-main smart-race-page">'+
      (row?smartRaceHead(row):'')+
      '<div class="smart-loading"><span class="smart-loading-dot"></span><b>'+(state.error?'取得済み情報を維持して再取得中':'レース情報を読み込み中')+'</b><small>'+(state.error?'通信が不安定でも画面は閉じません。取得できた情報から表示を続けます。':'選択したレースだけ取得しています。開催場一覧は先に表示します。')+'</small>'+(state.error&&row?'<button type="button" class="smart-refresh" data-race="'+esc(row.id)+'">再取得</button>':'')+'</div>'+
    '</main>'+cinematicFooter()+
  '</div>'
}
