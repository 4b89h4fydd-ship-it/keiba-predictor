function betComboText(kind,combos){
  combos=combos||[];
  function j(c,sep){return (c||[]).join(sep)}
  if(kind==='単勝')return combos.map(function(c){return j(c,'')}).join('・');
  if(kind==='馬単'||kind==='3連単')return combos.map(function(c){return j(c,' → ')}).join(' / ');
  return combos.map(function(c){return j(c,' - ')}).join(' / ')
}
