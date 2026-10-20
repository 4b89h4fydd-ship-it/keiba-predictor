function fetchEdgeRace(id,forceNetwork,retryLimit){
  if(!id)return Promise.resolve(null);
  var key=String(id),cached=instantTrackDetails[key]||loadDetailCache(id,true),row=(state.races||[]).find(function(x){return String(x&&x.id||'')===key})||null;
  // Historical summary/card caches can predate D1 learned publication.
  // Revalidate them on race open instead of permanently pinning old marks.
  // In a network outage, the existing cached racecard is retained below.

  var st=detailState(id),maxAttempts=retryLimit||2;
  st.error='';st.busy=true;st.attempts=0;
  updateDetailSections(id,cached||row,false);
  function attempt(index){
    var url=edgeRaceUrl(id);st.attempts=index+1;
    traceRaceDetail(id,'request',{attempt:index+1,url:url,date:(row||cached||{}).date||state.date,venue:(row||cached||{}).track,raceNo:(row||cached||{}).raceNumber});
    var revisionsUrl='https://kraiz-api.4b89h4fydd.workers.dev/api/forecast-revisions/'+encodeURIComponent(key)+'?t='+Date.now();
    return Promise.all([edgeFetchJson(url,9000),edgeFetchJson(revisionsUrl,6000).catch(function(){return null})]).then(function(responses){
      var body=responses[0],revisionBody=responses[1];
      if(!body||body.ok===false)throw Error('race detail response unavailable');
      var d=body.detail||null;
      if(d&&d.result&&d.result.finishers!=null&&!Array.isArray(d.result.finishers)){
        traceRaceDetail(id,'section-failed',{section:'result',message:'invalid finishers payload'});
        d=Object.assign({},d);delete d.result
      }
      if(d&&d.id&&String(d.id)!==key)throw Error('race detail id mismatch: '+d.id);
      if(body.race_id&&String(body.race_id)!==key)throw Error('response race id mismatch: '+body.race_id);
      var summary=normalizeDetailSummary(body.summary||row,id);
      if(String(summary.id)!==key)throw Error('summary race id mismatch: '+summary.id);
      var merged=mergeRaceReflection(cached,d,Array.isArray(body.odds)?body.odds:[],summary);
      // Basic fields returned by /api/day must survive sparse detail responses.
      merged=mergeRaceReflection(normalizeDetailSummary(row,id),merged,null,null);
      if(!d&&!entryDataAvailable(merged))throw Error('racecard unavailable');
      if(!entryDataAvailable(merged)&&!(d&&Array.isArray(d.horses)&&Number(d.fieldSize)===0&&d.fieldSize!=null))throw Error('racecard incomplete');
      if(revisionBody&&revisionBody.ok&&String(revisionBody.raceId)===key&&revisionBody.currentForecastRevisionId){
        merged.forecastRevisions=revisionBody.forecastRevisions;
        merged.currentForecastRevisionId=revisionBody.currentForecastRevisionId;
        if(!latestSavedForecastRevision(merged))throw Error('invalid saved forecast revision');
        delete merged._prediction;
      }
      if(d&&!d._entryOnly){merged._entryOnly=false;delete merged._staticRacecardFallback}
      if(body.analysis_ready)merged.preparedMeta=Object.assign({},merged.preparedMeta||{},{diagnosisReady:true});
      st.error='';updateDetailSections(id,merged,true);
      traceRaceDetail(id,'loaded',{attempt:index+1,horses:(merged.horses||[]).length,sections:Object.assign({},st)});
      instantTrackDetails[key]=merged;saveDetailCache(id,merged);return merged
    }).catch(function(error){
      traceRaceDetail(id,'failed',{attempt:index+1,url:url,message:String(error&&error.message||error)});
      var message=String(error&&error.message||error);
      if(index+1<maxAttempts&&!/http (?:404|400)/i.test(message))return new Promise(function(resolve){setTimeout(resolve,(index+1)*1000)}).then(function(){return attempt(index+1)});
      st.error=message;updateDetailSections(id,cached||row,false);
      // Immutable pre-race archives remain for audits, not live roster recovery.
      return entryDataAvailable(cached)?cached:null
    })
  }
  return attempt(0).finally(function(){st.busy=false})
}

