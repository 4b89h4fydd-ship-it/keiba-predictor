function currentBodyWeight(h){
  if(!h)return 0;var vals=[h.bodyWeight,h.horseWeight,h.currentBodyWeight];
  for(var i=0;i<vals.length;i++){
    var m=String(vals[i]==null?'':vals[i]).match(/(?:^|\D)(\d{3})(?:\D|$)/),w=m?n(m[1],0):n(vals[i],0);
    if(w>=250&&w<=800)return Math.round(w)
  }
  return 0
}
