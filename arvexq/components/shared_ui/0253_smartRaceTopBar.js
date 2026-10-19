function smartRaceTopBar(r){
  var rows=(state.races||[]).filter(function(x){return x&&r&&x.circuit===r.circuit&&x.track===r.track}).sort(function(a,b){return n(a.raceNumber)-n(b.raceNumber)}),idx=-1;
  for(var i=0;i<rows.length;i++){if(String(rows[i].id)===String(r.id)){idx=i;break}}
  var prev=idx>0?rows[idx-1]:null,next=idx>=0&&idx<rows.length-1?rows[idx+1]:null;
  return '<header class="smart-topbar smart-topbar-clean smart-race-topbar">'+
    '<span class="smart-pull-space" aria-hidden="true"></span>'+ 
    (prev?'<button class="smart-race-step prev" data-race="'+esc(prev.id)+'" data-preserve-panel="1" aria-label="前のレース">&lt;</button>':'<button class="smart-race-step prev" disabled>&lt;</button>')+
    '<div class="smart-head-copy smart-head-copy-clean smart-race-head-copy"><strong>'+esc(r.track)+' '+esc(r.raceNumber)+'R</strong></div>'+ 
    (next?'<button class="smart-race-step next" data-race="'+esc(next.id)+'" data-preserve-panel="1" aria-label="次のレース">&gt;</button>':'<button class="smart-race-step next" disabled>&gt;</button>')+
    '<button class="smart-race-close" data-action="back" aria-label="開催場のレース一覧へ戻る">×</button>'+ 
  '</header>'
}
