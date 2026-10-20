function scheduleVenueTrendRefresh(delay){
  if(venueTrendTimer){clearTimeout(venueTrendTimer);venueTrendTimer=null}
  if(!state.track||state.race||state.picker)return;
  var minWait=Math.max(0,10000-(Date.now()-venueTrendLastFetch)),wait=Math.max(n(delay,350),minWait);
  venueTrendTimer=setTimeout(function(){venueTrendTimer=null;refreshVenueTrendData()},wait)
}
