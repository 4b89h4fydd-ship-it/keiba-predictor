function paceStagePack(p,key){
  var plan=activeScenarioPlan(p)||p.plan||{},st=((plan.stages||[]).find(function(z){return String(z&&z.key||'')===key}))||{};
  return (st.pack||[]).slice()
}
