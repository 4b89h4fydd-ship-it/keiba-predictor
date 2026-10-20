function aiStoredMarks(detail){
  // Only verifiable pre-off snapshots count. Live horse evaluation is not evidence.
  var server=authorizedPreOffMarks(detail),saved=[];
  if(server)saved=server.horses.map(function(x){return {no:n(x.horseNumber),mark:String(x.mark||''),p:n(x.decisionProbability,0),confidence:n(server.winnerConfidence,0)}});
  else if(local){
    var off=Date.parse(String(detail.date||'')+'T'+String(detail.scheduledStartTime||detail.startTime||'').slice(0,5)+':00+09:00'),at=Date.parse(String(local.fixedAt||''));
    if(isFinite(off)&&isFinite(at)&&at<off)saved=local.marks.map(function(x){return {no:n(x.no),mark:String(x.mark||''),p:0,confidence:0}});
  }
  return saved.filter(function(x){return x.no>0})
}
