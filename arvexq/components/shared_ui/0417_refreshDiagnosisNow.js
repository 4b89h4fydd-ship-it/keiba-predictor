function refreshDiagnosisNow(id){
  if(!id||!state.race)return;
  state.diagnosisBusy=false;
  state.analysisSaved={};
  try{delete state.race._prediction}catch(e){}
  state.pred=null;
  render()
}
