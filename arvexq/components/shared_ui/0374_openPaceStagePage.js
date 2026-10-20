function openPaceStagePage(idx){
  state.paceStage=clamp(n(idx,0),0,PACE_STAGE_PAGES.length-1);
  state.subPageReturnPanel='pace';
  state.openPanel='pace';
  state.subPage='pace-stage';
  window.scrollTo(0,0);
  render()
}
