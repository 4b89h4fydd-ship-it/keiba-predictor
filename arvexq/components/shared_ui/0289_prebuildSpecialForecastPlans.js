function prebuildSpecialForecastPlans(){
  var picks=specialForecastRaceCandidates();
  picks.forEach(function(r){
    var id=String(r&&r.id||''),detail=id?(instantTrackDetails[id]||loadDetailCache(id)):null;
    if(!detail||isFinal(detail))return;
    var st=mins(detail.startTime||r.startTime),started=(detail.date||r.date)===today()&&st<9999&&nowMins()>=st;
    if(started)return;
    try{var p=predict(detail);buildAiBetPlan(detail,p)}catch(e){}
  })
}
