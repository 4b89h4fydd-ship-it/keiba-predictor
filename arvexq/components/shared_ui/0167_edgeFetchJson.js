function edgeFetchJson(url,timeoutMs){
  timeoutMs=n(timeoutMs,6500);
  var controller=(typeof AbortController!=='undefined')?new AbortController():null,timer=null,opts={cache:'no-store'};
  if(controller){opts.signal=controller.signal;timer=setTimeout(function(){try{controller.abort()}catch(e){}},timeoutMs)}
  return fetch(url,opts).then(function(res){if(!res.ok)throw Error('http '+res.status);return res.json()}).finally(function(){if(timer)clearTimeout(timer)})
}
// Each section retains its own readiness; failed requests never enter the detail cache.
var raceDetailStates={},raceDetailTrace=[];
