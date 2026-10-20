function refreshVenueTrendData(){
  if(venueTrendBusy||!state.track||state.race||state.picker)return Promise.resolve(false);
  var viewKey=[state.date,state.circuit,state.track].join('|'),date=state.date,track=state.track,circuit=state.circuit;
  venueTrendBusy=true;venueTrendLastFetch=Date.now();
  return fetch('https://kraiz-api.4b89h4fydd.workers.dev/api/day?date='+encodeURIComponent(date)+'&details=0&t='+Date.now(),{cache:'no-store'})
    .then(function(res){if(!res.ok)throw Error('venue-day '+res.status);return res.json()})
    .then(function(body){
      var rows=(body&&body.races)||[],changed=false;
      rows.forEach(function(z){
        if(String(z.track||'')!==String(track)||String(z.circuit||'')!==String(circuit))return;
        var r=state.races.find(function(x){return String(x&&x.id||'')===String(z.id||'')});if(!r)return;
        ['raceStatus','startTime','scheduledStartTime','weather','condition','title','surface','distance'].forEach(function(k){if(z[k]!=null&&z[k]!==''&&r[k]!==z[k]){r[k]=z[k];changed=true}})
      });
      return changed
    }).catch(function(){return false})
    .then(function(summaryChanged){
      if([state.date,state.circuit,state.track].join('|')!==viewKey)return summaryChanged;
      var now=nowMins(),todayView=date===today(),targets=venueRows().filter(function(r){
        if(!r||!r.id)return false;
        var started=!todayView||(r.startTime&&mins(r.startTime)<=now-1);
        return started&&(!trendResultReady(r)||isFlash(r)||!isFinal(r))
      }),cursor=0,changed=!!summaryChanged,workers=[];
      function worker(){
        if(cursor>=targets.length)return Promise.resolve();
        var row=targets[cursor++];
        return fetchEdgeRace(row.id,true).then(function(d){if(d&&mergeVenueTrendDetail(d))changed=true}).catch(function(){}).then(worker)
      }
      for(var i=0;i<Math.min(4,targets.length);i++)workers.push(worker());
      return Promise.all(workers).then(function(){return changed})
    }).then(function(changed){
      if(changed&&[state.date,state.circuit,state.track].join('|')===viewKey)render();
      return changed
    }).finally(function(){
      venueTrendBusy=false;
      if(state.track&&!state.race&&!state.picker&&state.date===today())scheduleVenueTrendRefresh(12000)
    })
}
