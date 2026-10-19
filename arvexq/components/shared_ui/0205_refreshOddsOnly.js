function refreshOddsOnly(force){
  if(!state.race||state.oddsBusy)return Promise.resolve(false);
  var id=String(state.race.id||''),seq=state.detailSeq;if(!id)return Promise.resolve(false);
  state.oddsBusy=true;
  var status=document.getElementById('odds-status');if(status)status.textContent=' 最新データ確認中…';
  return fetchSelectedRaceOdds(id,seq,force).finally(function(){
    state.oddsBusy=false;
    if(seq===state.detailSeq&&state.race&&String(state.race.id)===id)ensureAutoOdds(state.race)
  })
}
