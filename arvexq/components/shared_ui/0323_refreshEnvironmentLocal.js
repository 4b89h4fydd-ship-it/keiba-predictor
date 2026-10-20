function refreshEnvironmentLocal(track,attempt){
  track=track||state.track;
  if(!track||state.environmentBusy)return;
  state.environmentBusy=true;
  fetch(
    'https://kraiz-api.4b89h4fydd.workers.dev/api/day?date='
    +encodeURIComponent(state.date)
    +'&details=0&t='+Date.now(),
    {cache:'no-store'}
  )
    .then(function(res){
      if(!res.ok)throw Error('edge-environment '+res.status);
      return res.json()
    })
    .then(function(body){
      var rows=(body&&body.races)||[];
      rows=rows.filter(function(x){
        return String(x.track||'')===String(track)
          &&String(x.circuit||'')===String(state.circuit||'')
      });
      if(mergeEnvironmentPack(rows))render()
    })
    .catch(function(){})
    .finally(function(){state.environmentBusy=false})
}


