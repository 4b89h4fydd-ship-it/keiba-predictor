function scheduleRaceBiasRefresh(delay){
  if(raceBiasTimer){clearTimeout(raceBiasTimer);raceBiasTimer=null}
  var r=state.race;if(!r||String(r.date||'')!==today())return;
  raceBiasTimer=setTimeout(function(){raceBiasTimer=null;refreshRaceBiasData()},Math.max(500,n(delay,1200)))
}
