function applySummaryEnvironment(detail){
  if(!detail||!detail.id)return detail;
  var row=state.races.find(function(x){return String(x.id)===String(detail.id)});
  if(!row)return detail;
  ['track','date','raceNumber','title','distance','startTime','scheduledStartTime','fieldSize','surface','circuit'].forEach(function(k){
    if(!reflectUseful(detail[k])&&reflectUseful(row[k]))detail[k]=row[k]
  });
  var changed=false;
  ['weather','condition'].forEach(function(k){
    if(validEnvironmentValue(row[k])&&detail[k]!==row[k]){detail[k]=row[k];changed=true}
  });
  if(row.environmentMeta)detail.environmentMeta=row.environmentMeta;
  if(changed){
    try{delete detail._prediction}catch(e){}
    state.pred=null
  }
  return detail
}
