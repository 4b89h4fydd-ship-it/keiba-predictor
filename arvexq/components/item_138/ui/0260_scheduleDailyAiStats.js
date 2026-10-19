function scheduleDailyAiStats(){
  if(dailyAiStats.date!==state.date)resetDailyAiStats(state.date);
  if(dailyAiStats.loading)return;
  var targetDate=state.date,dayRaces=(state.races||[]).filter(function(r){return r&&r.id});
  var finals=dayRaces.filter(function(r){return isFinal(r)});
  if(!finals.length){dailyAiStats.done=false;dailyAiStats.total=0;dailyAiStats.finalCount=0;return}
  if(dailyAiStats.done&&dailyAiStats.finalCount===finals.length)return;
  var token=++dailyAiStatsJob,cursor=0,results=[];dailyAiStats.loading=true;dailyAiStats.done=false;dailyAiStats.error='';
  render();
  function worker(){
    if(token!==dailyAiStatsJob||cursor>=finals.length)return Promise.resolve();
    var row=finals[cursor++];
    return fetchEdgeRace(row.id,false).then(function(d){
      var z=aiDailyOne(d);
      if(z){
        z.hasMarks=true;z.resultReady=true;z.loadError=false;results.push(z)
      }else{
        var fs=(d&&d.result&&d.result.finishers||[]).filter(function(x){return n(x.finish)>0}).sort(function(a,b){return n(a.finish)-n(b.finish)}),marks=aiStoredMarks(d||{});
        results.push({raceId:String(row.id||''),track:String((d&&d.track)||row.track||''),raceNumber:n((d&&d.raceNumber)||row.raceNumber),title:String((d&&d.title)||row.title||''),circuit:String((d&&d.circuit)||row.circuit||''),winHit:false,markHit:false,fullPodiumHit:false,markedPodiumCount:0,holePlace:false,top2:false,top3:false,candidateOrderMiss:false,candidateMiss:!marks.length,highConf:false,highConfHit:false,brier:0,logLoss:0,reason:marks.length?'結果未取得':'発走前予想未保存',winner:n(fs[0]&&fs[0].horseNumber),winnerMark:'',podiumNos:fs.slice(0,3).map(function(x){return n(x.horseNumber)}).filter(function(x){return x>0}),marks:marks.filter(function(x){return !!String(x.mark||'')}).map(function(x){return{no:x.no,mark:x.mark}}),hasMarks:marks.length>0,resultReady:fs.some(function(x){return n(x.finish)===3}),eligible:false,triEligible:false,triHit:false,loadError:false})
      }
    }).catch(function(){
      results.push({raceId:String(row.id||''),track:String(row.track||''),raceNumber:n(row.raceNumber),title:String(row.title||''),circuit:String(row.circuit||''),marks:[],podiumNos:[],winHit:false,markHit:false,fullPodiumHit:false,markedPodiumCount:0,hasMarks:false,resultReady:false,eligible:false,triEligible:false,triHit:false,loadError:true})
    }).then(worker)
  }
  Promise.all([worker(),worker()]).then(function(){
    if(token!==dailyAiStatsJob||state.date!==targetDate)return;
    results.sort(function(a,b){var c=String(a.circuit||'').localeCompare(String(b.circuit||''),'ja');if(c)return c;var t=String(a.track||'').localeCompare(String(b.track||''),'ja');return t||n(a.raceNumber)-n(b.raceNumber)});
    dailyAiStats.loading=false;dailyAiStats.done=true;dailyAiStats.rows=results;dailyAiStats.total=results.filter(function(x){return x.eligible}).length;dailyAiStats.finalCount=finals.length;
    dailyAiStats.honPlaceHits=results.filter(function(x){return x.eligible&&x.honPlaceHit}).length;
    dailyAiStats.triTotal=results.filter(function(x){return x.eligible&&x.triEligible}).length;
    dailyAiStats.triHits=results.filter(function(x){return x.eligible&&x.triEligible&&x.triHit}).length;
    dailyAiStats.winHits=results.filter(function(x){return x.winHit}).length;
    dailyAiStats.markHits=results.filter(function(x){return x.markHit}).length;
    dailyAiStats.fullPodiumHits=results.filter(function(x){return x.fullPodiumHit}).length;
    dailyAiStats.markedPodiumSum=results.reduce(function(a,x){return a+n(x.markedPodiumCount)},0);
    dailyAiStats.centralPodiumTotal=results.filter(function(x){return x.circuit==='中央'}).length;dailyAiStats.centralPodiumHits=results.filter(function(x){return x.circuit==='中央'&&x.fullPodiumHit}).length;
    dailyAiStats.localPodiumTotal=results.filter(function(x){return x.circuit==='地方'}).length;dailyAiStats.localPodiumHits=results.filter(function(x){return x.circuit==='地方'&&x.fullPodiumHit}).length;
    dailyAiStats.holePlaceHits=results.filter(function(x){return x.holePlace}).length;
    dailyAiStats.top2Hits=results.filter(function(x){return x.top2}).length;
    dailyAiStats.top3Hits=results.filter(function(x){return x.top3}).length;
    dailyAiStats.candidateOrderMisses=results.filter(function(x){return x.candidateOrderMiss}).length;
    dailyAiStats.candidateMisses=results.filter(function(x){return x.candidateMiss}).length;
    dailyAiStats.highConfTotal=results.filter(function(x){return x.highConf}).length;
    dailyAiStats.highConfHits=results.filter(function(x){return x.highConfHit}).length;
    dailyAiStats.brierSum=results.reduce(function(a,x){return a+n(x.brier)},0);dailyAiStats.logLossSum=results.reduce(function(a,x){return a+n(x.logLoss)},0);
    dailyAiStats.reasons={};results.forEach(function(x){if(x.winHit)return;var k=x.reason||'その他';dailyAiStats.reasons[k]=(dailyAiStats.reasons[k]||0)+1});
    render()
  }).catch(function(){if(token!==dailyAiStatsJob)return;dailyAiStats.loading=false;dailyAiStats.done=true;dailyAiStats.error='集計できませんでした';render()})
}

