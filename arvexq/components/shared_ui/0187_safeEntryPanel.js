function safeEntryPanel(r,p){
  try{return runnerStyleSection(r,p)}catch(error){
    traceRaceDetail(r.id,'section-failed',{section:'entry-decoration',message:String(error&&error.message||error)});
    return minimalRacecardPanel(r)
  }
}
var racePredictionTasks=new WeakMap();
