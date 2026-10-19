function smartLiveCircuitGroup(circuit,label,now){
  var source=state.races.filter(function(r){return r.circuit===circuit}),tracks=[],seen={};
  source.forEach(function(r){var t=String(r.track||'');if(t&&!seen[t]){seen[t]=1;tracks.push(t)}});
  tracks.sort(function(a,b){return a.localeCompare(b,'ja')});
  var rows=tracks.map(function(track){return smartLiveVenueRace(source.filter(function(r){return r.track===track}),now)}).filter(Boolean);
  if(!rows.length)return'';
  return '<div class="smart-live-circuit"><div class="smart-live-circuit-head"><b>'+esc(label)+'</b><small>'+rows.length+'会場</small></div><div class="smart-live-strip">'+
    rows.map(function(r){
      var d=mins(r.startTime)-now,status=d<0?'進行中':(d<=10?'まもなく':d+'分後'),cls=d<0?'running':(d<=10?'soon':'upcoming');
      return '<button type="button" class="smart-live-card '+cls+'" data-race="'+esc(r.id)+'">'+
        '<small>'+esc(r.track)+' '+esc(r.raceNumber)+'R</small>'+ 
        '<b>'+esc(r.title||((r.track||'')+' '+n(r.raceNumber)+'R'))+'</b>'+ 
        '<strong>'+esc(r.startTime||'--:--')+'</strong>'+ 
        '<span class="smart-live-status">'+esc(status)+'</span>'+ 
        '<em>'+esc(r.surface||'')+' '+esc(r.distance||'—')+'m</em>'+ 
      '</button>'
    }).join('')+
  '</div></div>'
}
