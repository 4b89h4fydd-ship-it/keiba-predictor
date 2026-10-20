function saneCarriedWeightValue(v,bodyWeight){
  if(v==null||v==='')return 0;
  var raw=String(v).replace(/[^0-9.+-]/g,''),x=parseFloat(raw);
  if(!isFinite(x)||x<=0)return 0;
  // Never infer a 3-digit value as 斤量. A wrong 461kg→46.1kg conversion is
  // much worse than showing “—”; upstream parsers must provide kg correctly.
  if(x>=35&&x<=80)return Math.round(x*10)/10;
  return 0
}
