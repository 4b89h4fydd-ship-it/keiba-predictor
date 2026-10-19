function marketPopularity(h,r){
  var race=r||(state&&state.race),field=(race&&race.horses)||[];
  if(!h||isScratchHorse(h)||!(n(h.winOdds)>0))return 0;
  var active=field.filter(function(z){return z&&n(z.horseNumber)>0&&!isScratchHorse(z)});
  if(active.length<2)return 0;
  var forecast=!!h.oddsForecast||/予想|forecast/i.test(String(h.oddsSource||''));
  if(active.some(function(z){
    return !(z.winOdds!=null&&z.winOdds!==''&&isFinite(Number(z.winOdds))&&Number(z.winOdds)>0)||
      (!!z.oddsForecast||/予想|forecast/i.test(String(z.oddsSource||'')))!==forecast;
  }))return 0;
  return 1+active.filter(function(z){return Number(z.winOdds)<Number(h.winOdds)}).length;
}
