function liveVenueOptions(){
  var rows=[],seen={};
  (state.races||[]).forEach(function(r){var c=String(r.circuit||''),t=String(r.track||'');if(!t)return;var k=c+'|'+t;if(seen[k])return;seen[k]=1;rows.push({circuit:c,track:t})});
  rows.sort(function(a,b){if(a.circuit!==b.circuit)return a.circuit==='中央'?-1:1;return a.track.localeCompare(b.track,'ja')});
  return rows
}
