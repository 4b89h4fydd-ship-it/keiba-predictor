function paceStageRows(p,key){
  var plan=activeScenarioPlan(p)||p.plan||{},st=((plan.stages||[]).find(function(s){return String(s&&s.key||'')===key}))||{},by={};
  (p.rows||[]).forEach(function(x){by[n(x.horse&&x.horse.horseNumber)]=x});
  return (st.pack||[]).map(function(z){return by[n(z.no)]}).filter(Boolean)
}
