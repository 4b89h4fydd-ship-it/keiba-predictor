function smartVenueGroup(circuit,label){
  var rows=state.races.filter(function(x){return x.circuit===circuit}),
      tracks=[],seen={},waiting=!rows.length&&state.loading,
      countText=waiting?'準備中':rows.length+'レース';
  rows.forEach(function(r){
    var t=String(r.track||'');
    if(t&&!seen[t]){seen[t]=1;tracks.push(t)}
  });
  tracks.sort(function(a,b){return a.localeCompare(b,'ja')});
  var progress=state.bootstrapProgress||{},waitText='全レースデータを読み込み中';
  if(waiting&&n(progress.total)>0)waitText+='　'+n(progress.ready)+' / '+n(progress.total);
  return '<section class="smart-section smart-group-section">'+
    '<div class="smart-section-title smart-group-title"><div><b>'+esc(label)+'</b><small>開催場</small></div><span>'+esc(countText)+'</span></div>'+
    '<div class="smart-venue-grid">'+
      (tracks.length?tracks.map(function(track){
        var rs=rows.filter(function(x){return x.track===track}).sort(function(a,b){return n(a.raceNumber)-n(b.raceNumber)}),
            first=rs[0],last=rs[rs.length-1];
        return '<button class="smart-venue-card smart-venue-card-one" data-track="'+esc(track)+'" data-circuit="'+esc(circuit)+'">'+
          '<span class="smart-venue-mark">'+esc(track.slice(0,1))+'</span>'+
          '<span class="smart-venue-name"><b>'+esc(track)+'</b></span>'+
          '<span class="smart-venue-count">'+rs.length+'レース</span>'+
          '<span class="smart-venue-times"><small>'+(first?timeHtml(first):'--:--')+'</small><i>–</i><small>'+(last?timeHtml(last):'--:--')+'</small></span>'+
          '<span class="smart-chevron">›</span>'+
        '</button>'
      }).join(''):(waiting?'<div class="smart-empty">'+esc(waitText)+'</div>':'<div class="smart-empty">本日の開催情報はまだありません</div>'))+
    '</div>'+
  '</section>'
}
