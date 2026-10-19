function detailState(id){
  var key=String(id);
  return raceDetailStates[key]||(raceDetailStates[key]={basic:'loading',entry:'loading',odds:'loading',diagnosis:'loading',history:'loading',pace:'loading',result:'loading',payouts:'loading',busy:false,error:'',attempts:0})
}
