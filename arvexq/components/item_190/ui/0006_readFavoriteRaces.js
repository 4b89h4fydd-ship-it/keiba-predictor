function readFavoriteRaces(){
  try{
    var rows=JSON.parse(localStorage.getItem(FAVORITE_RACES_KEY)||"[]");
    if(!Array.isArray(rows))return [];
    var seen={};
    return rows.filter(function(r){
      if(!r||!r.id||!/^\d{4}-\d{2}-\d{2}$/.test(String(r.date||"")))return false;
      var key=String(r.date)+"|"+String(r.id);
      if(seen[key])return false;seen[key]=true;return true
    }).slice(-100)
  }catch(e){return []}
}
var favoriteRaces=readFavoriteRaces();
