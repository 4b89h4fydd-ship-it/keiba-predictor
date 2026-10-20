function mergeEnvironmentPack(rows){
  var map={},changed=false;
  (rows||[]).forEach(function(x){if(x&&x.id)map[String(x.id)]=x});
  state.races.forEach(function(r){
    var z=map[String(r.id)];if(!z)return;
    ['weather','condition'].forEach(function(k){
      if(validEnvironmentValue(z[k])&&r[k]!==z[k]){r[k]=z[k];changed=true}
    });
    if(z.environmentMeta)r.environmentMeta=z.environmentMeta
  });
  if(state.race){
    var z=map[String(state.race.id)];
    if(z){
      var raceChanged=false;
      ['weather','condition'].forEach(function(k){
        if(validEnvironmentValue(z[k])&&state.race[k]!==z[k]){state.race[k]=z[k];raceChanged=true;changed=true}
      });
      if(z.environmentMeta)state.race.environmentMeta=z.environmentMeta;
      if(raceChanged){
        try{delete state.race._prediction}catch(e){}
        state.pred=null;state.analysisSaved={};saveDetailCache(state.race.id,state.race)
      }
    }
  }
  if(changed)persistRaceSummaryCache();
  return changed
}
