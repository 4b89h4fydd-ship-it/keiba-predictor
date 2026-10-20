function smartVenueCards(){
  var hasCentral=state.races.some(function(x){return x.circuit==='中央'}),
      hasLocal=state.races.some(function(x){return x.circuit==='地方'}),html='';
  if(hasCentral)html+=smartVenueGroup('中央','中央');
  if(hasLocal)html+=smartVenueGroup('地方','地方');
  if(!html)html='<div class="smart-empty">開催場データを準備中です</div>';
  return '<div class="smart-home-list-heading"><b>開催場の一覧</b></div><div class="smart-group-wrap">'+html+'</div>'
}

