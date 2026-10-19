function refreshHomeOfficialStatuses(){
  if(homeOfficialStatusBusy||document.visibilityState==='hidden'||state.date!==today()||
     state.race||state.raceLoading||state.picker||state.homePage||!state.races.length)
    return Promise.resolve(false);
  var shared=window.ARVEXQUnifiedHome;
  if(!shared||typeof shared.mergePublishedStatuses!=='function')return Promise.resolve(false);
  var now=Date.now();
  if(now-homeOfficialStatusLastFetch<30000)return Promise.resolve(false);
  homeOfficialStatusLastFetch=now;homeOfficialStatusBusy=true;
  var date=state.date,seq=state.requestSeq;
  return fetch('https://kraiz-api.4b89h4fydd.workers.dev/api/day?date='+
    encodeURIComponent(date)+'&details=0&t='+now,{cache:'no-store'})
    .then(function(res){if(!res.ok)throw Error('official-status '+res.status);return res.json()})
    .then(function(body){
      if(seq!==state.requestSeq||state.date!==date||state.race||state.homePage)return false;
      var rows=Array.isArray(body)?body:body&&body.races;
      if(!Array.isArray(rows)||!rows.length)return false;
      var changed=shared.mergePublishedStatuses(state.races,rows);
      if(changed){
        saveRaceCache(date,'__ALL__',state.races);
        shared.syncLiveUI('horse',state.races,date,document);
      }
      return !!changed;
    }).catch(function(){return false})
    .finally(function(){homeOfficialStatusBusy=false});
}
setInterval(function(){
  if(document.visibilityState==='hidden'||state.date!==today()||state.race||state.raceLoading||
     state.picker||state.homePage)return;
  var shared=window.ARVEXQUnifiedHome;
  if(!shared||!document.querySelector('.smart-shell.smart-home .arv-all-panel,.smart-venue-page .smart-race-row'))return;
  shared.syncLiveUI('horse',state.races||[],state.date,document);
  refreshHomeOfficialStatuses();
},10000);
installNavigation();installEdgeBack();installPullRefresh();installPwaCache();evictRetiredRaceCaches();normalizeInitialAppLaunch();restoreLocation();setTimeout(load,0);
})();
