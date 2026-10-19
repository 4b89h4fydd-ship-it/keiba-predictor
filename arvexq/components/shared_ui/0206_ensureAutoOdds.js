function ensureAutoOdds(r){
  if(state.oddsTimer){clearTimeout(state.oddsTimer);state.oddsTimer=null}
  if(!r||r.date!==today()||isFinal(r)||!entryDataAvailable(r))return;
  var id=String(r.id),seq=state.detailSeq;
  state.oddsTimer=setTimeout(function(){
    if(seq===state.detailSeq&&state.race&&String(state.race.id)===id)refreshOddsOnly(false)
  },raceOddsComplete(r)?15000:8000)
}
