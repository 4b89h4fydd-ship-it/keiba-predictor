function mergeVenueTrendDetail(d){
  if(!d||!d.id)return false;
  var id=String(d.id),changed=false,r=state.races.find(function(x){return String(x&&x.id||'')===id});
  instantTrackDetails[id]=d;saveDetailCache(id,d);
  if(r){
    if(d.result&&hasAnyResultData(d)){
      var before=JSON.stringify(r.result||null),after=JSON.stringify(d.result||null);
      if(before!==after){r.result=d.result;changed=true}
      if(d.result.status&&r.raceStatus!==d.result.status){r.raceStatus=d.result.status;changed=true}
    }
    ['weather','condition','oddsUpdatedAt','environmentMeta'].forEach(function(k){if(d[k]!=null&&d[k]!==''&&d[k]!=='不明'&&r[k]!==d[k]){r[k]=d[k];changed=true}})
  }
  return changed
}
