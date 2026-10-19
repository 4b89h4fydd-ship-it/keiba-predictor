function racecardOddsHtml(h,r){
  if(isScratchHorse(h))return '<span class="odd scratch-odds">取消</span><span class="pop scratch-note">出走取消</span>';
  var valid=h&&h.winOdds!=null&&h.winOdds!==''&&n(h.winOdds)>0,
      value=valid?n(h.winOdds):0,pop=marketPopularity(h,r),
      forecast=!!(h&&h.oddsForecast)||/予想|forecast/i.test(String(h&&h.oddsSource||''));
  return '<span class="odd '+(value>0&&value<10?'single':'')+'">'+esc(valid?(Math.round(value*10)/10).toFixed(1):'未取得')+'</span>'
    +'<span class="pop">'+(forecast?'予想 ':'')+(pop>0?esc(pop)+'人気':'未取得')+'</span>';
}
