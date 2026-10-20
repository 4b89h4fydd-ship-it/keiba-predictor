function mainRaceForTrack(rows){
  rows=(rows||[]).filter(function(r){return r&&r.id}).slice().sort(function(a,b){return n(a.raceNumber)-n(b.raceNumber)});if(!rows.length)return null;
  var explicit=rows.find(function(r){var role=String(r.raceRole||r.role||r.raceType||'').toLowerCase();return r.isMain===true||r.mainRace===true||role==='main'||role==='mainrace'||/メイン/.test(String(r.title||''))});if(explicit)return explicit;
  var featured=rows.find(function(r){return r.featured===true});if(featured)return featured;
  var r11=rows.find(function(r){return n(r.raceNumber)===11});if(r11)return r11;
  return rows[rows.length-1]
}
