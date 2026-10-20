function goBack(){
    if(!canGoBack())return;
    if(state.subPage){
        // A stale subPage flag must not consume the race-level × click. Only
        // a visibly rendered child screen gets its own close navigation.
        var nestedVisible=!!document.querySelector('[data-action="close-race-subpage"]');
        state.subPage=null;state.openPanel=state.subPageReturnPanel||'entry';state.subPageReturnPanel=null;
        if(nestedVisible){window.scrollTo(0,0);render();return}
    }
    if(state.horseModalNo){
        if(document.querySelector('.horse-modal-layer')){closeHorseModal();return}
        state.horseModalNo=null
    }
    ++state.detailSeq;
    if(state.historyTimer){clearTimeout(state.historyTimer);state.historyTimer=null}
    if(state.collectTimer){clearTimeout(state.collectTimer);state.collectTimer=null}
    state.collectingHorse=null;state.error=null;state.pred=null;state.scenarioCode=null;state.paceStage=0;

    if(state.raceLoading||state.race){
        if(state.raceStack.length){
            // A past-race detail returns to the race detail that opened it.
            state.raceLoading=null;
            state.race=state.raceStack.pop();
            state.picker=false;
            if(state.race&&state.race.track)state.track=state.race.track
        }else if(state.raceReturnHomePage){
            state.raceLoading=null;state.race=null;state.picker=false;state.track=null;
            state.homePage=state.raceReturnHomePage;state.pickCircuit=state.raceReturnPickCircuit||null;
            state.raceReturnHomePage=null;state.raceReturnPickCircuit=null
        }else{
            // A normal race detail returns to this venue's full race list.
            var keepTrack=state.track||(state.race&&state.race.track)||"";
            state.raceLoading=null;
            state.race=null;
            state.picker=false;
            state.track=keepTrack||null
        }
    }else if(state.picker){
        state.picker=false;
        state.track=null
    }else if(state.track){
        state.track=null;
        state.picker=false
    }else if(state.aiStatsTrack){
        state.aiStatsTrack=null
    }else if(state.pickCircuit){
        state.pickCircuit=null
    }else if(state.homePage){
        state.homePage=null;
        state.pickCircuit=null;
        state.aiStatsTrack=null
    }

    // Do not use browser history for the × button; keep app hierarchy deterministic.
    routeKey=null;
    render();
    window.scrollTo(0,0)
}
var navigationRestoring=false,routeKey=null;
