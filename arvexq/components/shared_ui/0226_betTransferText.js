function betTransferText(r,p){
  var plan=buildAiBetPlan(r,p);
  if(!plan)return '';
  var lines=['ARVEXQ おすすめ買い目',String(r.track||'')+' '+String(r.raceNumber||'')+'R '+String(r.title||''),'発走 '+String(r.startTime||'--:--')];
  (plan.items||[]).forEach(function(z){lines.push(String(z.level||'')+'｜'+String(z.kind||'')+'｜'+String(z.combo||'')+'｜'+String(z.points||0)+'点'+(z.confidence?'｜'+String(z.confidence):''))});
  if(plan.trifectaReviewed&&plan.trifectaDecision==='見送り')lines.push('3連単｜検討済み｜順序信頼不足で見送り｜'+String(plan.orderScore||0)+'/100');
  lines.push('※投票内容・金額は公式投票サイトで確認して確定してください。');
  return lines.join('\n')
}
