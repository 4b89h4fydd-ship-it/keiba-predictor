function raceDetailNotice(r){
  var st=detailState(r.id),staticNotice=r&&r._staticRacecardFallback?
    '<div class="diagnosis-refresh-note" role="status">保存済みの出走表を表示中です。取消・騎手変更・オッズの最新情報は未確認です。</div>':'';
  if(r&&r._resultIdentityError)staticNotice+='<div class="diagnosis-refresh-note">結果の馬番・馬名が出走表と一致しないため表示を保留しています。</div>';
  if(r&&r._rosterIdentityError)staticNotice+='<div class="diagnosis-refresh-note">APIの出走馬不一致を検出し、検証済みの出走表を表示しています。</div>';
  if(!st.error)return staticNotice;
  return staticNotice+'<div class="diagnosis-refresh-note" role="status">'+(entryDataAvailable(r)?'取得済みの出走表を表示しています。':'レース基本情報を表示しています。')+' 詳細の更新に失敗しました。 <button type="button" data-detail-retry="'+esc(r.id)+'">再試行</button></div>'
}
