function schedulePreviousAiStats(){
  var targetDate=previousDateKey(today());
  if(!targetDate)return;
  if(previousAiStats.date!==targetDate)resetPreviousAiStats(targetDate);
  if(previousAiStats.loading||previousAiStats.done)return;
  // Race opening/current-day preload always has priority over yesterday's audit.
  if(state.raceLoading||state.race||state.track||state.picker)return;
  if(state.date===today()&&!selectedRacePreload.fullLoaded){
    setTimeout(function(){if(!previousAiStats.done&&!previousAiStats.loading)schedulePreviousAiStats()},2500);
    return
  }
  var token=++previousAiStatsJob;previousAiStats.loading=true;previousAiStats.error='';render();
  edgeFetchJson('https://kraiz-api.4b89h4fydd.workers.dev/api/day?date='+encodeURIComponent(targetDate)+'&details=0&t='+Date.now(),9000)
    .then(function(body){
      if(token!==previousAiStatsJob)return null;
      var rows=Array.isArray(body)?body:((body&&body.races)||[]);
      rows=rows.filter(function(r){return r&&r.id});
      previousAiStats.finalCount=rows.length;
      var cursor=0,results=rows.map(function(row){
        return {
          raceId:String(row.id||''),track:String(row.track||''),raceNumber:n(row.raceNumber),
          title:String(row.title||''),circuit:String(row.circuit||''),marks:[],podiumNos:[],
          winHit:false,markHit:false,fullPodiumHit:false,markedPodiumCount:0,
          hasMarks:false,resultReady:false,loadError:false
        }
      }),workers=[];
      function worker(){
        if(token!==previousAiStatsJob||cursor>=rows.length)return Promise.resolve();
        var idx=cursor++,row=rows[idx],id=String(row.id||'');
        return edgeFetchJson(edgeRaceUrl(id),9000)
          .then(function(body){
            var d=body&&body.detail?body.detail:null;
            if(!d){results[idx].loadError=true;return}
            if(!d.track)d.track=row.track;if(!d.raceNumber)d.raceNumber=row.raceNumber;if(!d.title)d.title=row.title;if(!d.circuit)d.circuit=row.circuit;
            var finishers=(d.result&&d.result.finishers||[]).filter(function(x){return n(x.finish)>0}).sort(function(a,b){return n(a.finish)-n(b.finish)});
            results[idx].resultReady=finishers.length>0;
            results[idx].podiumNos=finishers.slice(0,3).map(function(x){return n(x.horseNumber)}).filter(function(x){return x>0});
            var marks=aiStoredMarks(d);
            results[idx].hasMarks=marks.length>0;
            results[idx].marks=marks.filter(function(x){return !!String(x.mark||'')}).map(function(x){return{no:x.no,mark:x.mark}});
            var z=aiDailyOne(d);
            if(z){
              z.hasMarks=true;z.resultReady=results[idx].resultReady;z.loadError=false;
              results[idx]=z
            }
          })
          .catch(function(){results[idx].loadError=true})
          .then(worker)
      }
      // Keep yesterday's audit strictly low priority: one request at a time.
      if(rows.length)workers.push(worker());
      return Promise.all(workers).then(function(){return results})
    })
    .then(function(results){
      if(token!==previousAiStatsJob||!results)return;
      results.sort(function(a,b){var c=String(a.circuit||'').localeCompare(String(b.circuit||''),'ja');if(c)return c;var t=String(a.track||'').localeCompare(String(b.track||''),'ja');return t||n(a.raceNumber)-n(b.raceNumber)});
      previousAiStats.loading=false;previousAiStats.done=true;previousAiStats.rows=results;previousAiStats.total=results.length;
      previousAiStats.winHits=results.filter(function(x){return x.winHit}).length;
      previousAiStats.markHits=results.filter(function(x){return x.markHit}).length;
      previousAiStats.fullPodiumHits=results.filter(function(x){return x.fullPodiumHit}).length;
      previousAiStats.markedPodiumSum=results.reduce(function(a,x){return a+n(x.markedPodiumCount)},0);
      render()
    })
    .catch(function(err){
      if(token!==previousAiStatsJob)return;
      previousAiStats.loading=false;previousAiStats.done=true;previousAiStats.error=String(err&&err.message||'前日AI成績を取得できませんでした');render()
    })
}
