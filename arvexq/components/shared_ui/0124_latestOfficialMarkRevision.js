function latestOfficialMarkRevision(r){
  var initial=validMorningMarkSnapshot(r);
  if(!initial)return null;
  var post=Date.parse(String(r.date||'')+'T'+String(r.startTime||r.scheduledStartTime||'').slice(0,5)+':00+09:00'),
      latest=null;
  (r.officialMarkRevisions||[]).forEach(function(z){
    if(!z||z.version!=='arvexq-official-mark-revision-v1'||
        String(z.raceId||'')!==String(r.id)||String(z.raceDate||'')!==String(r.date)||
        !Array.isArray(z.horses)||z.horses.length<3)return;
    var at=Date.parse(String(z.revisedAt||'')),
        announced=Date.parse(String((z.officialCourseCondition||{}).publishedAt||'')),
        url=String((z.officialCourseCondition||{}).sourceUrl||'');
    if(!isFinite(at)||!isFinite(announced)||at>=post||announced>at||!/^https:\/\//.test(url))return;
    if(!latest||Date.parse(String(latest.revisedAt||''))<at)latest=z
  });
  return latest
}
