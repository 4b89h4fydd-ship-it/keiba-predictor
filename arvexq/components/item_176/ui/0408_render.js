function render(){
  var savedY=window.scrollY;
  syncLocation();stopTimer();
  try{
    var view=state.raceLoading?renderRaceLoading():(state.race?renderRace():(state.picker?renderPicker():(state.track?renderVenue():(state.homePage?renderHomeSectionPage():renderHome()))));
    app.innerHTML=view+smartTodayReturn();
    arvexqBootPainted=true;
    syncLiveCenterOverlay();
    bind();
    if(entryDataAvailable(state.race)&&state.race._prediction){initPaceBoard();ensureAutoOdds(state.race);scheduleRaceBiasRefresh(700)}
    else if(state.track&&!state.picker){scheduleVenueTrendRefresh(350)}
    // The result and payout lane must work even when AI diagnosis is unavailable.
    if(state.race) scheduleResultRefresh();
    if(entryDataAvailable(state.race))ensureAutoOdds(state.race)
    window.scrollTo(0,savedY)
  }catch(e){
    try{console.error('ARVEXQ render recovery',e)}catch(_e){}
    try{
      if(app){
        var old=app.querySelector('#arvexq-runtime-recovery');if(old)old.remove();
        var note=document.createElement('div');note.id='arvexq-runtime-recovery';note.className='diagnosis-refresh-note busy';
        note.setAttribute('role','status');note.style.margin='8px 12px';
        note.textContent='一部データを再取得中です。表示できている情報はそのまま維持します。';
        app.insertBefore(note,app.firstChild);
        try{bind()}catch(_bindError){}
        setTimeout(function(){try{if(note&&note.parentNode)note.parentNode.removeChild(note)}catch(_removeError){}},2200)
      }
    }catch(_uiError){}
  }
}
