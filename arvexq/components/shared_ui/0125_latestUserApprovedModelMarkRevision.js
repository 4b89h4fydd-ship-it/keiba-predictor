function latestUserApprovedModelMarkRevision(r){
  var initial=validMorningMarkSnapshot(r);
  if(!initial||String(r.date)!=='2026-10-09')return null;
  var post=Date.parse(String(r.date||'')+'T'+String(r.startTime||r.scheduledStartTime||'').slice(0,5)+':00+09:00'),
      approval=Date.parse('2026-10-09T20:10:00+09:00'),fixed=Date.parse(String(initial.fixedAt||'')),
      expected={};
  (initial.horses||[]).forEach(function(h){expected[n(h.horseNumber,0)]=true});
  var count=Object.keys(expected).length,latest=null;
  (r.modelMarkRevisions||[]).forEach(function(z){
    if(!z||z.version!=='arvexq-user-model-mark-revision-v1'||
       z.approvalId!=='user-approved-past-five-from-2026-10-09-20-10-jst'||
       z.modelVersion!=='arvexq-axis-reliability-v2-past-context'||
       String(z.raceId||'')!==String(r.id)||String(z.raceDate||'')!==String(r.date)||
       !Array.isArray(z.horses)||z.horses.length!==count)return;
    var at=Date.parse(String(z.revisedAt||'')),seen={},valid=true;
    if(!isFinite(at)||at<approval||at<=fixed||at>=post)return;
    z.horses.forEach(function(h){
      var no=n(h&&h.horseNumber,0),mark=String(h&&h.mark||'');
      if(!no||!expected[no]||seen[no]||['','◎','○','▲','☆+','☆','△','注'].indexOf(mark)<0)valid=false;
      seen[no]=true
    });
    if(!valid)return;
    if(!latest||Date.parse(String(latest.revisedAt||''))<at)latest=z
  });
  return latest
}
