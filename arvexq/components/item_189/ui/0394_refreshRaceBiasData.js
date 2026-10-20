function refreshRaceBiasData(){
  var r=state.race;if(raceBiasBusy||!r||String(r.date||'')!==today())return Promise.resolve(false);
  var id=String(r.id||''),raceNo=n(r.raceNumber,99),now=nowMins(),targets=(state.races||[]).filter(function(z){
    if(!z||String(z.date||'')!==String(r.date||'')||String(z.circuit||'')!==String(r.circuit||'')||String(z.track||'')!==String(r.track||''))return false;
    if(n(z.raceNumber,99)>=raceNo)return false;
    if(mins(z.startTime)>now-2)return false;
    return !trendResultReady(z)
  }).sort(function(a,b){return n(b.raceNumber)-n(a.raceNumber)}).slice(0,6),before=sameDayTrendSignatureV313(r,(state.pred&&state.pred.rows)||buildRows(analysisRace(r)));
  if(!targets.length){scheduleRaceBiasRefresh(12000);return Promise.resolve(false)}
  raceBiasBusy=true;var cursor=0,changed=false,workers=[];
  function worker(){
    if(cursor>=targets.length)return Promise.resolve();var z=targets[cursor++];
    return fetchEdgeRace(z.id,true).then(function(d){if(d){if(mergeVenueTrendDetail(d))changed=true}}).catch(function(){}).then(worker)
  }
  for(var i=0;i<Math.min(3,targets.length);i++)workers.push(worker());
  return Promise.all(workers).then(function(){
    if(!state.race||String(state.race.id)!==id)return false;
    var after=sameDayTrendSignatureV313(state.race,(state.pred&&state.pred.rows)||buildRows(analysisRace(state.race)));
    if(changed||before!==after){try{delete state.race._prediction}catch(e){}state.pred=null;render();return true}
    return false
  }).finally(function(){raceBiasBusy=false;if(state.race&&String(state.race.id)===id)scheduleRaceBiasRefresh(12000)})
}
// Results are fetched independently of prediction/diagnosis readiness.
// A re-render (for example from odds updates) must not postpone the polling timer.
var resultPollBusy=false,resultPollActiveId='';
