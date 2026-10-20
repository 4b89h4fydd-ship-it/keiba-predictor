function warmTrackSnapshots(track,high){
  track=track||state.track;
  if(!track)return Promise.resolve(0);

  var key=[state.date,state.circuit,track].join('|');
  if(trackSnapshotJobs[key])return trackSnapshotJobs[key];

  var targets=(state.races||[])
    .filter(function(r){
      return r&&r.id
        &&String(r.track||'')===String(track)
        &&String(r.circuit||'')===String(state.circuit||'')
    })
    .sort(function(a,b){
      return n(a.raceNumber)-n(b.raceNumber)
    });

  // Cloudflare is fast enough to warm a venue directly.
  // Do not wake Render just to prepare cards.
  var cursor=0,count=0,workers=[];
  var concurrency=Math.min(4,Math.max(1,targets.length));

  function worker(){
    if(cursor>=targets.length)return Promise.resolve();
    var row=targets[cursor++];
    var needLiveResult=state.date===today()&&mins(row.startTime)<=nowMins()-3&&!isFinal(row);
    return fetchEdgeRace(row.id,needLiveResult)
      .then(function(d){if(d)count++})
      .then(worker)
  }

  for(var i=0;i<concurrency;i++)workers.push(worker());

  trackSnapshotJobs[key]=Promise.all(workers)
    .then(function(){return count})
    .catch(function(){return count})
    .finally(function(){delete trackSnapshotJobs[key]});

  return trackSnapshotJobs[key]
}

