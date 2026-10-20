function evictRetiredRaceCaches(){
  try{
    var marker="arvexq:race-source-schema";
    if(localStorage.getItem(marker)===ARVEXQ_RACE_CACHE_SCHEMA)return;
    for(var i=localStorage.length-1;i>=0;i--){
      var key=String(localStorage.key(i)||"");
      if(/^arvexq:[^:]+:(races|fullbundle|detail):/.test(key))localStorage.removeItem(key);
    }
    localStorage.setItem(marker,ARVEXQ_RACE_CACHE_SCHEMA)
  }catch(e){}
}
