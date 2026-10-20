function returnToToday(){
  if(state.oddsTimer){clearTimeout(state.oddsTimer);state.oddsTimer=null}
  if(state.environmentTimer){clearTimeout(state.environmentTimer);state.environmentTimer=null}
  if(state.historyTimer){clearTimeout(state.historyTimer);state.historyTimer=null}
  state.raceStack=[];++state.detailSeq;state.raceLoading=null;state.date=today();state.openPanel=null;state.race=null;state.track=null;state.picker=false;state.horseModalNo=null;state.detailHorseNo=null;state.subPage=null;state.subPageReturnPanel=null;state.subPage=null;state.subPageReturnPanel=null;state.scenarioCode=null;state.paceStage=0;
  window.scrollTo(0,0);load()
}
