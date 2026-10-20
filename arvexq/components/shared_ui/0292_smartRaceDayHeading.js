function smartRaceDayHeading(){
  var parts=String(state.date||'').split('-'),m=n(parts[1]),d=n(parts[2]),isToday=state.date===today(),
      hasCentral=state.races.some(function(x){return x.circuit==='中央'}),
      hasLocal=state.races.some(function(x){return x.circuit==='地方'});
  var title=isToday?'本日のレース':(m&&d?m+'月'+d+'日のレース':'開催レース');
  var sub=isToday?(hasCentral&&hasLocal?'今日の中央・地方開催':(hasCentral?'今日の中央開催':(hasLocal?'今日の地方開催':'今日の開催'))):((state.date||'').replace(/-/g,'.')+' の開催');
  return '<section class="smart-race-day-heading"><div><b>'+esc(title)+'</b><small>'+esc(sub)+'</small></div></section>'
}
