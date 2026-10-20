function moveDetailHorse(dir){
  if(!state.pred)return;var rows=sortedHorseRows(state.pred.rows);if(!rows.length)return;
  var idx=rows.findIndex(function(z){return n(z.horse.horseNumber)===n(state.detailHorseNo)});if(idx<0)idx=0;
  state.detailHorseNo=n(rows[(idx+dir+rows.length)%rows.length].horse.horseNumber);state.subPage='horse';render()
}
