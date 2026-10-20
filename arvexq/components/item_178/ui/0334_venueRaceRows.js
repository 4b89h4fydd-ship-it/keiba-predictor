function venueRaceRows(){
  var info=venueHeaderInfo(),rows=info.rows,isTodayView=info.isTodayView,now=info.now,nextId=info.nextId;
  return venueTrendCard()+
    '<section class="smart-section smart-race-section">'+
    '<div class="smart-race-list">'+
      Array.from({length:12},function(_,idx){
        var no=idx+1,r=rows.find(function(x){return n(x.raceNumber)===no});
        if(!r)return '<div class="smart-race-row disabled"><strong>'+no+'R</strong><span class="smart-race-time">--:--</span><span class="smart-race-title">レース情報待ち</span><span></span></div>';
        var fin=isFinal(r),flash=isFlash(r),isNext=isTodayView&&String(r.id||'')===nextId,
            lifecycle=window.ARVEXQUnifiedHome&&window.ARVEXQUnifiedHome.raceStatus?
              window.ARVEXQUnifiedHome.raceStatus('horse',r,state.date,new Date()):
              (fin||flash?'finished':(isTodayView&&r.startTime&&mins(r.startTime)<now?'elapsed':'upcoming')),
            cls=fin||flash||lifecycle==='elapsed'||lifecycle==='finished'?'final':
              (lifecycle==='running'?'running':(lifecycle==='soon'?'soon':(isNext?'next-race':''))),
            label=fin?'確定':(flash?'速報':(window.ARVEXQUnifiedHome?window.ARVEXQUnifiedHome.labelFor(lifecycle):'')),
            stateTag='<span class="race-state-pill arv-race-state">'+esc(label||'')+'</span>';
        return '<div class="arv-favorite-venue-item"><button class="smart-race-row '+cls+'" data-race="'+esc(r.id)+'" data-race-state="'+esc(lifecycle)+'">'+
          '<strong>'+no+'R</strong>'+ 
          '<span class="smart-race-time">'+(fin?'確定':(flash?'速報':timeHtml(r)))+'</span>'+ 
          '<span class="smart-race-title">'+stateTag+'<b>'+esc(r.title||no+'R')+'</b><small>'+esc(r.surface||'')+' '+esc(r.distance||'—')+'m　'+esc((r.weather&&r.weather!=='不明')?r.weather:'天候待ち')+' / '+esc((r.condition&&r.condition!=='不明')?r.condition:'馬場待ち')+'</small></span>'+ 
          '<span class="smart-chevron">›</span>'+ 
        '</button>'+favoriteStarHtml(r,'arv-venue-favorite-star')+'</div>'
      }).join('')+
    '</div>'+ 
  '</section>'
}
