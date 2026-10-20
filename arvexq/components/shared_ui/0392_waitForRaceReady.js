function waitForRaceReady(id,seq,attempt){
  attempt=n(attempt,0);
  if(seq!==state.detailSeq)return;
  setTimeout(function(){
    if(seq!==state.detailSeq)return;
    fetchEdgeRace(id).then(function(body){
      if(seq!==state.detailSeq)return;
      if(body){
        state.raceLoading=null;
        state.race=applySummaryEnvironment(body);
        render();
        return
      }
      if(attempt<4){
        waitForRaceReady(id,seq,attempt+1);
        return
      }
      state.raceLoading=null;
      state.error='Cloudflare同期待ちです。少し後でもう一度更新してください。';
      render()
    })
  },500+attempt*350)
}

var raceBiasTimer=null,raceBiasBusy=false;
