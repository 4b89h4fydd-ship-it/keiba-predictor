function venueHeaderInfo(){
  var rows=venueRows(),isTodayView=state.date===today(),now=nowMins(),futureRows=[],nextId='',status='1R〜12R';
  if(isTodayView){
    futureRows=rows.filter(function(x){return !isFinal(x)&&x.startTime&&mins(x.startTime)>=now}).sort(function(a,b){return mins(a.startTime)-mins(b.startTime)});
    if(futureRows.length){nextId=String(futureRows[0].id||'');status='次のレース '+n(futureRows[0].raceNumber)+'R '+String(futureRows[0].startTime||'')}
    else if(rows.length&&rows.every(function(x){return isFinal(x)}))status='本日のレース終了'
  }
  return {rows:rows,isTodayView:isTodayView,now:now,nextId:nextId,status:status}
}
var venueTrendTimer=null,venueTrendBusy=false,venueTrendLastFetch=0;
