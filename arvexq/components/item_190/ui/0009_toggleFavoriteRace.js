function toggleFavoriteRace(id,date){
  var keyDate=String(date||state.date),idx=favoriteRaces.findIndex(function(x){return String(x.id)===String(id)&&String(x.date)===keyDate});
  var next=favoriteRaces.slice();
  if(idx>=0)next.splice(idx,1);
  else{
    var r=state.races.find(function(x){return String(x.id)===String(id)&&String(x.date||state.date)===keyDate})||
      (state.race&&String(state.race.id)===String(id)?state.race:null);
    if(!r)return;
    next.push({id:String(r.id),date:keyDate,circuit:String(r.circuit||state.circuit),track:String(r.track||state.track||''),raceNumber:n(r.raceNumber),title:String(r.title||''),startTime:String(r.startTime||'')});
    next=next.slice(-100)
  }
  try{localStorage.setItem(FAVORITE_RACES_KEY,JSON.stringify(next))}
  catch(e){try{window.alert('お気に入りを保存できませんでした。ブラウザの保存設定をご確認ください。')}catch(_e){}return}
  favoriteRaces=next;render()
}
