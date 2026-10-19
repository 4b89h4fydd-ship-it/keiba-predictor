function fastReflectNow(){
  if(document.visibilityState==='hidden'||liveCenterOpen)return;
  var now=Date.now();if(now-n(fastReflectNow._lastAt,0)<2500)return;fastReflectNow._lastAt=now;
  try{
    if(state.race&&state.race.id){refreshOddsOnly(true);return}
    if(!state.track&&!state.picker&&typeof fastTopRefresh==='function')fastTopRefresh()
  }catch(e){}
}
window.addEventListener('pageshow',function(){setTimeout(fastReflectNow,120)},{passive:true});
document.addEventListener('visibilitychange',function(){if(document.visibilityState==='visible')setTimeout(fastReflectNow,120)},{passive:true});
// The 10-second clock repaint alone cannot discover published official results:
// it only sees yesterday's in-memory race summary. Every 30 seconds, retrieve
// the lightweight D1 summary and merge ONLY official result states. This does
// not refresh odds/diagnoses or rewrite frozen pre-race evaluations.
var homeOfficialStatusBusy=false,homeOfficialStatusLastFetch=0;
