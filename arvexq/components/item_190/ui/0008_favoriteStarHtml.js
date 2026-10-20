function favoriteStarHtml(r,extraClass){
  var active=isFavoriteRace(r);
  return '<button type="button" class="arv-favorite-star '+(extraClass||'')+(active?' active':'')+'" data-favorite-toggle="'+esc(r.id)+'" data-favorite-date="'+esc(r.date||state.date)+'" aria-label="'+(active?'お気に入りから解除':'お気に入りレースに登録')+'" aria-pressed="'+active+'" title="'+(active?'お気に入り解除':'お気に入り登録')+'">'+(active?'★':'☆')+'</button>'
}
