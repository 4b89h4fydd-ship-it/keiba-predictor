function paceStageConfig(idx){
  idx=clamp(n(idx,0),0,PACE_STAGE_PAGES.length-1);
  return Object.assign({index:idx},PACE_STAGE_PAGES[idx])
}
