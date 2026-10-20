function saveStoredAiBet(r,plan){
  try{
    if(!r||!r.id||!plan||isFinal(r))return;
    var st=mins(r.startTime),raceDate=String(r.date||''),todayKey=today(),started=(raceDate===todayKey&&st<9999&&nowMins()>=st);
    if(raceMarkClock(r).started||started||st>=9999||raceDate!==todayKey||loadStoredAiBet(r.id))return;
    var rd=plan.dataReadiness||{},central=String(r.circuit||'')==='中央',
        minReady=central?.62:.58,ready=Number(rd.prediction),remain=st-nowMins(),lockWindow=30,
        gate=plan.betInputGate||{};
    if(remain>lockWindow||remain<0)return;
    if(!isFinite(ready)||ready<minReady||gate.ready!==true)return;
    if(n(rd.card,0)<.90||n(rd.history,0)<.55||n(rd.analysis,0)<.45)return;
    plan.raceId=String(r.id);plan.raceDate=raceDate;plan.fixedAt=new Date().toISOString();plan.fixedBeforePost=true;plan.fixedMinutesBeforePost=Math.max(0,Math.round(remain));
    plan.fixedInputReadiness={prediction:n(rd.prediction,0),card:n(rd.card,0),history:n(rd.history,0),actualOdds:n(rd.actualOdds,0),bodyWeight:n(rd.bodyWeight,0),environment:n(rd.environment,0),analysis:n(rd.analysis,0)};
    plan.lockPolicy='v355-prerace-model-evidence-30m';
    plan.inputWarningsAtFreeze=(gate.warnings||[]).slice();
    localStorage.setItem(aiBetStoreKey(r.id),JSON.stringify(plan))
  }catch(e){}
}
