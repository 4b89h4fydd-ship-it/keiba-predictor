function isFavoriteRace(r){
  return !!r&&favoriteRaces.some(function(x){return String(x.id)===String(r.id)&&String(x.date)===String(r.date||state.date)})
}
